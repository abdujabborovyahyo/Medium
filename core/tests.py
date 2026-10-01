from django.test import TestCase
from django.urls import reverse


class PublicPagesTests(TestCase):
    def test_public_pages_render_for_anonymous_users(self):
        for name in ("core:home", "core:intro", "core:premium", "articles:list", "accounts:login", "accounts:signup"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
