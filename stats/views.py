from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from interactions.models import ArticleLike
from .models import DailyStats


@login_required
def stats_view(request):
    """
    Stats dashboard with charts and analytics.
    """
    user = request.user
    articles = user.articles.published()

    totals = articles.aggregate(total_views=Sum("views_count"))
    total_likes = ArticleLike.objects.filter(article__in=articles).count()
    total_followers = user.followers.count()

    # Last 30 days — one grouped query instead of 30 separate queries
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=29)
    per_day = {
        row["date"]: row
        for row in DailyStats.objects.filter(user=user, date__range=(start_date, end_date))
        .values("date")
        .annotate(views=Sum("views"), reads=Sum("reads"))
    }
    days = [start_date + timedelta(days=i) for i in range(30)]
    chart_data = {
        "labels": [d.strftime("%m-%d") for d in days],
        "views": [per_day.get(d, {}).get("views") or 0 for d in days],
        "reads": [per_day.get(d, {}).get("reads") or 0 for d in days],
    }

    context = {
        "total_views": totals["total_views"] or 0,
        "total_likes": total_likes,
        "total_followers": total_followers,
        "total_subscribers": total_followers,  # In future, distinguish subscribers
        "articles_count": articles.count(),
        "chart_data": chart_data,
        "followers": user.followers.select_related("follower")[:10],
        "following": user.following.select_related("following")[:10],
    }
    return render(request, "stats/stats.html", context)


@login_required
def audience_view(request):
    """
    Audience/followers detailed view.
    """
    user = request.user
    followers = user.followers.select_related('follower').order_by('-created_at')
    following = user.following.select_related('following').order_by('-created_at')

    context = {
        'followers': followers,
        'following': following,
        'followers_count': followers.count(),
        'following_count': following.count(),
    }

    return render(request, 'stats/audience.html', context)