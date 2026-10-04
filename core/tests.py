from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from articles.models import Article
from comments.models import Comment
from interactions.models import Bookmark, ReadingList, ReadingListItem
from notifications.models import Notification, ReadingHistory, UserFollowing


class PublicPagesTests(TestCase):
    def test_public_pages_render_for_anonymous_users(self):
        for name in ("core:home", "core:intro", "core:premium", "articles:list", "accounts:login", "accounts:signup"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_404_page(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Return Home", status_code=404)

    def test_premium_page_has_no_payment_form(self):
        self.assertNotContains(self.client.get(reverse("core:premium")), "Card information")


class AuthenticatedPagesTests(TestCase):
    """Every page renders with real data (catches template errors after refactors)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!", bio="Hi")
        other = CustomUser.objects.create_user("other", "o@example.com", "pass12345!")
        self.article = Article.objects.create(
            author=self.user, title="Story", body="<p>Text</p>", status="published", is_member_only=True
        )
        other_article = Article.objects.create(author=other, title="Other", body="<p>x</p>", status="published")
        UserFollowing.objects.create(follower=other, following=self.user)
        UserFollowing.objects.create(follower=self.user, following=other)
        Bookmark.objects.create(user=self.user, article=other_article)
        reading_list = ReadingList.objects.create(user=self.user, name="Later")
        ReadingListItem.objects.create(reading_list=reading_list, article=other_article)
        ReadingHistory.objects.create(user=self.user, article=other_article)
        comment = Comment.objects.create(article=self.article, author=other, body="Nice")
        Comment.objects.create(article=self.article, author=self.user, body="Thanks", parent=comment)
        Notification.objects.create(recipient=self.user, sender=other, notification_type="follow", title="other followed")
        Notification.objects.create(
            recipient=self.user, sender=other, notification_type="comment", title="c", article=self.article, comment=comment
        )
        self.list_id = reading_list.pk
        self.client.force_login(self.user)

    def test_pages_render(self):
        urls = [
            reverse("core:home"),
            reverse("articles:list"),
            reverse("articles:create"),
            self.article.get_absolute_url(),
            reverse("articles:edit", args=[self.article.slug]),
            reverse("articles:delete", args=[self.article.slug]),
            reverse("accounts:profile", args=["writer"]),
            reverse("accounts:profile", args=["other"]),
            reverse("accounts:profile_edit", args=["writer"]),
            reverse("accounts:logout"),
            reverse("interactions:library"),
            reverse("interactions:lists"),
            reverse("interactions:reading-list-detail", args=[self.list_id]),
            reverse("notifications:list"),
            reverse("notifications:reading-history"),
            reverse("stats:dashboard"),
            reverse("stats:audience"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_no_inline_styles_in_pages(self):
        response = self.client.get(self.article.get_absolute_url())
        self.assertNotContains(response, 'style="')
