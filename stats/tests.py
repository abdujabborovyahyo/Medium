from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from articles.models import Article
from .models import DailyStats


class StatsTests(TestCase):
    def test_dashboard_and_view_tracking(self):
        author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")
        reader = CustomUser.objects.create_user("reader", "r@example.com", "pass12345!")
        article = Article.objects.create(author=author, title="T", body="<p>x</p>", status="published")

        self.client.force_login(reader)
        self.client.get(article.get_absolute_url())
        self.assertEqual(DailyStats.objects.get(article=article).views, 1)

        self.client.force_login(author)
        response = self.client.get(reverse("stats:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["chart_data"]["views"][-1], 1)
        self.assertEqual(self.client.get(reverse("stats:audience")).status_code, 200)
