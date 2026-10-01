from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from articles.models import Article
from notifications.models import Notification


class ToggleTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")
        self.reader = CustomUser.objects.create_user("reader", "r@example.com", "pass12345!")
        self.article = Article.objects.create(author=self.author, title="T", body="<p>x</p>", status="published")
        self.client.force_login(self.reader)

    def test_like_toggle(self):
        url = reverse("interactions:like-toggle", args=[self.article.pk])
        self.assertEqual(self.client.post(url).json(), {"liked": True, "count": 1})
        self.assertEqual(self.client.post(url).json(), {"liked": False, "count": 0})
        self.assertTrue(Notification.objects.filter(recipient=self.author, notification_type="like").exists())

    def test_bookmark_toggle(self):
        url = reverse("interactions:bookmark-toggle", args=[self.article.pk])
        self.assertTrue(self.client.post(url).json()["saved"])
        self.assertFalse(self.client.post(url).json()["saved"])

    def test_add_to_list_validates_ids(self):
        response = self.client.post(reverse("interactions:add-to-list"), {"article_id": "abc", "list_name": "x"})
        self.assertEqual(response.status_code, 400)

    def test_add_to_list(self):
        response = self.client.post(
            reverse("interactions:add-to-list"), {"article_id": self.article.pk, "list_name": "Later"}
        )
        self.assertTrue(response.json()["added"])
        self.assertEqual(self.client.get(reverse("interactions:library")).status_code, 200)
