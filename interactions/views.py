from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from articles.models import Article
from notifications.models import Notification
from .models import ArticleLike, Bookmark, ReadingList, ReadingListItem


@require_POST
@login_required
def toggle_bookmark(request, article_id):
    article = get_object_or_404(Article.objects.published(), pk=article_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, article=article)

    if not created:
        bookmark.delete()
    elif article.author_id != request.user.pk:
        Notification.objects.create(
            recipient=article.author,
            sender=request.user,
            notification_type=Notification.Type.BOOKMARK,
            article=article,
            title=f"{request.user.username} saved your article",
            description=f"'{article.title}'",
        )

    return JsonResponse({"saved": created, "count": article.bookmarked_by.count()})


@require_POST
@login_required
def toggle_like(request, article_id):
    article = get_object_or_404(Article.objects.published(), pk=article_id)
    like, created = ArticleLike.objects.get_or_create(user=request.user, article=article)

    if not created:
        like.delete()
    elif article.author_id != request.user.pk:
        Notification.objects.create(
            recipient=article.author,
            sender=request.user,
            notification_type=Notification.Type.LIKE,
            article=article,
            title=f"{request.user.username} liked your article",
            description=f"'{article.title}'",
        )

    return JsonResponse({"liked": created, "count": article.likes.count()})


@login_required
def library_view(request):
    """
    Show user's library (bookmarked articles, lists, and notifications).
    """
    # 1. Bookmarks va Lists (Mavjud kod)
    bookmarks = request.user.bookmarks.select_related("article__author", "article").all()
    lists = request.user.reading_lists.annotate(items_total=Count("items"))

    # 2. Notifications (Xatoni to'g'irlash uchun qo'shilgan qism)
    # Bildirishnomalarni view ichida filtrlaymiz
    comment_notifications = request.user.notifications.filter(
        notification_type__in=['comment', 'reply']
    ).select_related('sender', 'article')

    context = {
        "bookmarks": bookmarks,
        "lists": lists,
        "comment_notifications": comment_notifications  # Shablonda shu nomdan foydalanamiz
    }

    return render(request, "interactions/library.html", context)


# ----- Reading list management -----
@login_required
@require_POST
def add_to_list(request):
    """
    POST params:
      - article_id (required)
      - list_id (optional) OR list_name (optional): if list_id provided, add to it; otherwise use or create list with list_name.
    Returns JSON: { success, list_id, list_name, added }
    """
    article_id = request.POST.get("article_id")
    list_id = request.POST.get("list_id")
    list_name = request.POST.get("list_name", "").strip()

    if not article_id or not article_id.isdigit() or (list_id and not list_id.isdigit()):
        return JsonResponse({"error": "A valid article_id is required"}, status=400)

    article = get_object_or_404(Article.objects.published(), pk=article_id)

    if list_id:
        reading_list = get_object_or_404(ReadingList, pk=list_id, user=request.user)
    else:
        if not list_name:
            return JsonResponse({"error": "Provide list_id or list_name"}, status=400)
        reading_list, _ = ReadingList.objects.get_or_create(user=request.user, name=list_name[:150])

    _, added = ReadingListItem.objects.get_or_create(reading_list=reading_list, article=article)
    return JsonResponse({
        "success": True,
        "list_id": reading_list.id,
        "list_name": reading_list.name,
        "added": added,
        "items_count": reading_list.items.count()
    })

@login_required
@require_POST
def remove_from_list(request):
    """
    POST: article_id, list_id
    """
    article_id = request.POST.get("article_id")
    list_id = request.POST.get("list_id")
    if not (article_id or "").isdigit() or not (list_id or "").isdigit():
        return JsonResponse({"error": "article_id and list_id required"}, status=400)

    reading_list = get_object_or_404(ReadingList, pk=list_id, user=request.user)
    ReadingListItem.objects.filter(reading_list=reading_list, article_id=article_id).delete()
    return JsonResponse({"success": True, "items_count": reading_list.items.count()})

@login_required
def lists_view(request):
    """
    Show user's lists with items.
    """
    lists = request.user.reading_lists.prefetch_related("items__article__author").all()
    return render(request, "interactions/lists.html", {"lists": lists})

@login_required
def reading_list_detail(request, list_id):
    reading_list = get_object_or_404(ReadingList, pk=list_id, user=request.user)
    items = reading_list.items.select_related("article__author").all()
    return render(request, "interactions/reading_list_detail.html", {"list": reading_list, "items": items})