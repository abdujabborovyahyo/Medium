from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from articles.models import Article
from interactions.models import ArticleLike
from .models import DailyStats

PERIODS = {7: "Last 7 days", 30: "Last 30 days", 90: "Last 3 months", 365: "Last year"}


@login_required
def stats_view(request):
    """
    Stats dashboard: totals + daily chart for the selected period.
    """
    user = request.user
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    if days not in PERIODS:
        days = 30

    articles = user.articles.published()
    totals = DailyStats.objects.filter(user=user).aggregate(reads=Sum("reads"))

    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=days - 1)
    per_day = {
        row["date"]: row
        for row in DailyStats.objects.filter(user=user, date__range=(start_date, end_date))
        .values("date")
        .annotate(views=Sum("views"), reads=Sum("reads"), likes=Sum("likes"))
    }
    dates = [start_date + timedelta(days=i) for i in range(days)]
    chart_data = {
        "labels": [d.strftime("%b %d") for d in dates],
        "views": [per_day.get(d, {}).get("views") or 0 for d in dates],
        "reads": [per_day.get(d, {}).get("reads") or 0 for d in dates],
        "likes": [per_day.get(d, {}).get("likes") or 0 for d in dates],
    }

    top_articles = articles.order_by("-views_count")[:5]

    context = {
        "articles_count": articles.count(),
        "total_views": articles.aggregate(total=Sum("views_count"))["total"] or 0,
        "total_reads": totals["reads"] or 0,
        "total_likes": ArticleLike.objects.filter(article__author=user).count(),
        "total_followers": user.followers.count(),
        "chart_data": chart_data,
        "days": days,
        "periods": PERIODS,
        "top_articles": top_articles,
    }
    return render(request, "stats/stats.html", context)


@login_required
def audience_view(request):
    """
    Followers and following lists.
    """
    user = request.user
    followers = user.followers.select_related("follower")
    following = user.following.select_related("following")

    return render(request, "stats/audience.html", {
        "followers": followers,
        "following": following,
        "followers_count": followers.count(),
        "following_count": following.count(),
    })


@require_POST
def record_read(request, article_id):
    """
    Called by the article page when the reader reaches the end of the story.
    Counted once per session; the author's own reads are ignored.
    """
    article = get_object_or_404(Article.objects.published().select_related("author"), pk=article_id)
    if not article.can_view(request.user):
        raise Http404

    session_key = f"read_article_{article.pk}"
    counted = False
    if request.user.pk != article.author_id and not request.session.get(session_key):
        DailyStats.change("reads", user_id=article.author_id, article_id=article.pk)
        request.session[session_key] = True
        counted = True
    return JsonResponse({"counted": counted})
