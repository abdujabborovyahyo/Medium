from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from articles.models import Article
from .models import DailyStats


class StatsTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")
        self.reader = CustomUser.objects.create_user("reader", "r@example.com", "pass12345!")
        self.article = Article.objects.create(author=self.author, title="T", body="<p>x</p>", status="published")

    def today(self, **filters):
        return DailyStats.objects.get(user=self.author, date=timezone.localdate(), **filters)

    def test_views_are_tracked_but_not_for_the_author(self):
        self.client.force_login(self.author)
        self.client.get(self.article.get_absolute_url())
        self.assertFalse(DailyStats.objects.exists())

        self.client.force_login(self.reader)
        self.client.get(self.article.get_absolute_url())
        self.assertEqual(self.today(article=self.article).views, 1)

    def test_read_counted_once_per_session(self):
        url = reverse("stats:record-read", args=[self.article.pk])
        self.assertTrue(self.client.post(url).json()["counted"])
        self.assertFalse(self.client.post(url).json()["counted"])
        self.assertEqual(self.today(article=self.article).reads, 1)

    def test_author_read_is_ignored(self):
        self.client.force_login(self.author)
        self.client.post(reverse("stats:record-read", args=[self.article.pk]))
        self.assertFalse(DailyStats.objects.exists())

    def test_likes_and_followers_are_counted(self):
        self.client.force_login(self.reader)
        like_url = reverse("interactions:like-toggle", args=[self.article.pk])
        self.client.post(like_url)
        self.assertEqual(self.today(article=self.article).likes, 1)
        self.client.post(like_url)  # unlike
        self.assertEqual(self.today(article=self.article).likes, 0)

        follow_url = reverse("notifications:follow", args=[self.author.pk])
        self.client.post(follow_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(self.today(article__isnull=True).followers_gained, 1)

    def test_only_one_profile_row_per_day(self):
        DailyStats.objects.create(user=self.author, article=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DailyStats.objects.create(user=self.author, article=None)

    def test_counter_never_goes_negative(self):
        DailyStats.change("likes", user_id=self.author.pk, article_id=self.article.pk, amount=-1)
        self.assertFalse(DailyStats.objects.exists())

    def test_dashboard(self):
        self.client.force_login(self.reader)
        self.client.get(self.article.get_absolute_url())
        self.client.post(reverse("stats:record-read", args=[self.article.pk]))

        self.client.force_login(self.author)
        response = self.client.get(reverse("stats:dashboard"), {"days": 7})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["chart_data"]["labels"]), 7)
        self.assertEqual(response.context["chart_data"]["views"][-1], 1)
        self.assertEqual(response.context["total_reads"], 1)
        self.assertEqual(self.client.get(reverse("stats:dashboard"), {"days": "abc"}).context["days"], 30)
        self.assertEqual(self.client.get(reverse("stats:audience")).status_code, 200)
