from django.db.models import Count
from django.shortcuts import render

from articles.models import Article
from articles.views import annotate_user_flags


def home(request):
    articles = (
        Article.objects.published()
        .select_related("author")
        .annotate(likes_total=Count("likes"))
    )
    articles = annotate_user_flags(articles, request.user)[:10]
    return render(request, "core/home.html", {"articles": articles})


def intro(request):
    return render(request, "core/intro.html")


def premium(request):
    return render(request, "core/premium.html")
