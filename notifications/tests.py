from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from .models import Notification, UserFollowing


class FollowTests(TestCase):
    def setUp(self):
        self.alice = CustomUser.objects.create_user("alice", "a@example.com", "pass12345!")
        self.bob = CustomUser.objects.create_user("bob", "b@example.com", "pass12345!")
        self.client.force_login(self.alice)
        self.url = reverse("notifications:follow", args=[self.bob.pk])

    def test_follow_toggle_sends_one_notification(self):
        ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        self.assertTrue(self.client.post(self.url, **ajax).json()["is_following"])
        self.assertFalse(self.client.post(self.url, **ajax).json()["is_following"])
        self.assertTrue(self.client.post(self.url, **ajax).json()["is_following"])
        self.assertEqual(Notification.objects.filter(recipient=self.bob, notification_type="follow").count(), 1)

    def test_cannot_follow_self(self):
        url = reverse("notifications:follow", args=[self.alice.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserFollowing.objects.exists())

    def test_redirect_ignores_foreign_referer(self):
        response = self.client.post(self.url, HTTP_REFERER="https://evil.example.com/")
        self.assertRedirects(response, reverse("accounts:profile", args=["bob"]))
