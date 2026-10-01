from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


class SignupTests(TestCase):
    def test_signup_page_renders(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertContains(response, "Create account")

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(reverse("accounts:signup"), {
            "username": "newbie",
            "email": "New@Example.com",
            "password1": "S3cure-pass-123",
            "password2": "S3cure-pass-123",
        })
        self.assertRedirects(response, reverse("core:home"))
        user = CustomUser.objects.get(username="newbie")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_is_rejected(self):
        CustomUser.objects.create_user("first", "taken@example.com", "pass12345!")
        response = self.client.post(reverse("accounts:signup"), {
            "username": "second",
            "email": "TAKEN@example.com",
            "password1": "S3cure-pass-123",
            "password2": "S3cure-pass-123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_signup_ignores_external_next_url(self):
        response = self.client.post(reverse("accounts:signup"), {
            "username": "newbie",
            "email": "n@example.com",
            "password1": "S3cure-pass-123",
            "password2": "S3cure-pass-123",
            "next": "https://evil.example.com/",
        })
        self.assertRedirects(response, reverse("core:home"))


class ProfileEditTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user("owner", "o@example.com", "pass12345!")
        CustomUser.objects.create_user("other", "x@example.com", "pass12345!")
        self.client.force_login(self.user)

    def test_invalid_username_does_not_break_page(self):
        # "other" is taken: the form is invalid, the page must still render
        response = self.client.post(
            reverse("accounts:profile_edit", args=["owner"]),
            {"username": "other", "email": "o@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts:profile", args=["owner"]))

    def test_cannot_edit_someone_else(self):
        response = self.client.get(reverse("accounts:profile_edit", args=["other"]))
        self.assertRedirects(response, reverse("accounts:profile", args=["owner"]))
