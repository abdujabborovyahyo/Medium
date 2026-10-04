import os
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.db.models import Count, Exists, F, OuterRef, Q
from django.http import Http404, JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from comments.models import Comment
from interactions.models import ArticleLike, Bookmark
from notifications.models import Notification, ReadingHistory, UserFollowing
from stats.models import DailyStats
from .forms import ArticleForm
from .models import Article


def annotate_user_flags(queryset, user):
    """Add user_has_liked / user_has_bookmarked flags for the current user."""
    if not user.is_authenticated:
        return queryset
    return queryset.annotate(
        user_has_liked=Exists(ArticleLike.objects.filter(article=OuterRef("pk"), user=user)),
        user_has_bookmarked=Exists(Bookmark.objects.filter(article=OuterRef("pk"), user=user)),
    )


def notify_followers_about(article):
    """Tell the author's followers that a new article was published."""
    author = article.author
    follower_ids = author.followers.values_list("follower_id", flat=True)
    Notification.objects.bulk_create(
        Notification(
            recipient_id=follower_id,
            sender=author,
            notification_type=Notification.Type.NEW_ARTICLE,
            article=article,
            title=f"{author.username} published a new article",
            description=f"'{article.title}'",
        )
        for follower_id in follower_ids
    )


class ArticleListView(ListView):
    model = Article
    template_name = "articles/article_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = (
            Article.objects.published()
            .select_related("author")
            .prefetch_related("tags")
            .annotate(likes_total=Count("likes", distinct=True))
        )

        qs = qs.search(self.request.GET.get("q"))

        tag = self.request.GET.get("tag", "").strip()
        if tag:
            qs = qs.filter(tags__slug=tag)

        return annotate_user_flags(qs, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Keep search/tag filters when moving between pages
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_string"] = params.urlencode()
        return context


class ArticleDetailView(DetailView):
    model = Article
    template_name = "articles/article_detail.html"

    def get_queryset(self):
        user = self.request.user
        qs = (
            Article.objects.visible_to(user)
            .select_related("author")
            .prefetch_related("tags")
            .annotate(
                likes_total=Count("likes", distinct=True),
                comments_total=Count("comments", filter=Q(comments__approved=True), distinct=True),
            )
        )
        qs = annotate_user_flags(qs, user)
        if user.is_authenticated:
            qs = qs.annotate(
                user_follows_author=Exists(
                    UserFollowing.objects.filter(following=OuterRef("author"), follower=user)
                )
            )
        return qs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.can_view(self.request.user):
            raise Http404("This article is for members only.")
        return obj

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        article = self.object

        if request.user.is_authenticated:
            ReadingHistory.objects.update_or_create(user=request.user, article=article)

        # Count one view per session, ignoring the author's own visits.
        # F() avoids lost updates and doesn't touch updated_at.
        session_key = f"viewed_article_{article.pk}"
        is_author = request.user.pk == article.author_id
        if article.is_published and not is_author and not request.session.get(session_key):
            Article.objects.filter(pk=article.pk).update(views_count=F("views_count") + 1)
            DailyStats.change("views", user_id=article.author_id, article_id=article.pk)
            request.session[session_key] = True

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_following"] = getattr(self.object, "user_follows_author", False)
        context["comments"] = Comment.tree_for(self.object)
        return context


class AuthorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.get_object().author_id == self.request.user.pk


class ArticleCreateView(LoginRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    template_name = "articles/article_form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        if self.object.is_published:
            notify_followers_about(self.object)
            messages.success(self.request, "Your article is published.")
        else:
            messages.success(self.request, "Draft saved.")
        return response


class ArticleUpdateView(LoginRequiredMixin, AuthorRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = "articles/article_form.html"

    def form_valid(self, form):
        was_published = Article.objects.filter(pk=form.instance.pk, status=Article.Status.PUBLISHED).exists()
        response = super().form_valid(form)
        if self.object.is_published and not was_published:
            notify_followers_about(self.object)
        messages.success(self.request, "Article updated.")
        return response


class ArticleDeleteView(LoginRequiredMixin, AuthorRequiredMixin, DeleteView):
    model = Article
    success_url = reverse_lazy("articles:list")
    template_name = "articles/article_confirm_delete.html"

    def form_valid(self, form):
        messages.success(self.request, "Article deleted successfully!")
        return super().form_valid(form)


def _upload_limit_for(content_type):
    """Return (kind, max_size) for an allowed MIME type, or (None, None)."""
    if content_type in settings.ALLOWED_IMAGE_TYPES:
        return "image", settings.IMAGE_MAX_UPLOAD_SIZE
    if content_type in settings.ALLOWED_VIDEO_TYPES:
        return "video", settings.VIDEO_MAX_UPLOAD_SIZE
    if content_type in settings.ALLOWED_FILE_TYPES:
        return "file", settings.FILE_MAX_UPLOAD_SIZE
    return None, None


ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp4", ".webm", ".ogg",
    ".pdf", ".txt", ".doc", ".docx",
}


@login_required
@require_POST
def upload_media(request):
    """
    Accepts a file via POST (field 'file') and stores it under MEDIA_ROOT/article_media/.
    Returns JSON: { url: <media_url>, name: <filename>, type: <image|video|file> }
    """
    the_file = request.FILES.get("file")
    if not the_file:
        return JsonResponse({"error": "No file provided."}, status=400)

    kind, max_size = _upload_limit_for(the_file.content_type or "")
    ext = os.path.splitext(the_file.name)[1].lower()
    if kind is None or ext not in ALLOWED_EXTENSIONS:
        return JsonResponse({"error": "Unsupported file type."}, status=400)
    if the_file.size > max_size:
        return JsonResponse({"error": f"File too large. Max size is {max_size // (1024 * 1024)} MB."}, status=400)

    # Random name: never trust the user's file name for the path
    saved_path = default_storage.save(f"article_media/{uuid.uuid4().hex}{ext}", the_file)
    return JsonResponse({"url": default_storage.url(saved_path), "name": the_file.name, "type": kind})
