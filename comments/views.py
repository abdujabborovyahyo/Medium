from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import truncatewords
from django.views.decorators.http import require_POST

from articles.models import Article
from notifications.models import Notification
from .models import Comment

MAX_COMMENT_LENGTH = 5000


@require_POST
@login_required
def add_comment(request):
    body = request.POST.get("body", "").strip()
    article_id = request.POST.get("article_id", "")
    parent_id = request.POST.get("parent_id", "")

    if not article_id.isdigit():
        raise Http404
    article = get_object_or_404(Article.objects.published(), pk=article_id)
    # Same rule as reading: can't comment on a member-only story you can't see
    if not article.can_view(request.user):
        raise Http404

    redirect_url = article.get_absolute_url() + "#comments"
    if not body:
        return redirect(redirect_url)
    if len(body) > MAX_COMMENT_LENGTH:
        messages.error(request, f"Comment is too long (max {MAX_COMMENT_LENGTH} characters).")
        return redirect(redirect_url)

    parent = None
    if parent_id.isdigit():
        parent = Comment.objects.approved().filter(pk=parent_id, article=article).select_related("author").first()

    approved = not settings.COMMENTS_REQUIRE_APPROVAL
    comment = Comment.objects.create(
        article=article, author=request.user, body=body, parent=parent, approved=approved
    )
    if not approved:
        messages.info(request, "Thanks! Your comment will appear after a moderator approves it.")
        return redirect(redirect_url)

    description = truncatewords(body, 15)

    if article.author_id != request.user.pk:
        Notification.objects.create(
            recipient=article.author,
            sender=request.user,
            notification_type=Notification.Type.COMMENT,
            article=article,
            comment=comment,
            title=f"{request.user.username} commented on your article",
            description=description,
        )

    # Reply: notify the parent comment's author (unless it's the same person or the deleted user)
    if parent and parent.author_id and parent.author_id not in (request.user.pk, article.author_id):
        Notification.objects.create(
            recipient=parent.author,
            sender=request.user,
            notification_type=Notification.Type.REPLY,
            article=article,
            comment=comment,
            title=f"{request.user.username} replied to your comment",
            description=description,
        )

    return redirect(f"{article.get_absolute_url()}#comment-{comment.pk}")
