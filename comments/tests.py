from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from articles.models import Article
from notifications.models import Notification
from .models import Comment


class CommentTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")
        self.reader = CustomUser.objects.create_user("reader", "r@example.com", "pass12345!")
        self.article = Article.objects.create(author=self.author, title="T", body="<p>x</p>", status="published")

    def test_comment_and_reply_notifications(self):
        self.client.force_login(self.reader)
        self.client.post(reverse("comments:add"), {"article_id": self.article.pk, "body": "Nice!"})
        comment = Comment.objects.get()
        self.assertTrue(Notification.objects.filter(recipient=self.author, notification_type="comment").exists())

        self.client.force_login(self.author)
        self.client.post(
            reverse("comments:add"),
            {"article_id": self.article.pk, "parent_id": comment.pk, "body": "Thanks"},
        )
        self.assertTrue(Notification.objects.filter(recipient=self.reader, notification_type="reply").exists())

    def test_cannot_comment_on_draft(self):
        draft = Article.objects.create(author=self.author, title="D", body="<p>x</p>", status="draft")
        self.client.force_login(self.reader)
        response = self.client.post(reverse("comments:add"), {"article_id": draft.pk, "body": "Hi"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Comment.objects.exists())

    def test_invalid_article_id_returns_404(self):
        self.client.force_login(self.reader)
        response = self.client.post(reverse("comments:add"), {"article_id": "abc", "body": "Hi"})
        self.assertEqual(response.status_code, 404)

    def test_comment_from_deleted_user_still_renders(self):
        Comment.objects.create(article=self.article, author=None, body="orphan")
        response = self.client.get(self.article.get_absolute_url())
        self.assertContains(response, "Deleted user")


class ModerationTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")
        self.reader = CustomUser.objects.create_user("reader", "r@example.com", "pass12345!")
        self.article = Article.objects.create(author=self.author, title="T", body="<p>x</p>", status="published")

    def test_hidden_comments_and_their_replies_are_not_shown(self):
        hidden = Comment.objects.create(article=self.article, author=self.reader, body="spam text", approved=False)
        Comment.objects.create(article=self.article, author=self.reader, body="reply to spam", parent=hidden)
        Comment.objects.create(article=self.article, author=self.reader, body="visible one")

        response = self.client.get(self.article.get_absolute_url())
        self.assertNotContains(response, "spam text")
        self.assertNotContains(response, "reply to spam")
        self.assertContains(response, "visible one")
        self.assertEqual(response.context["object"].comments_total, 2)  # approved rows (incl. orphan reply)

    def test_require_approval_setting(self):
        self.client.force_login(self.reader)
        with self.settings(COMMENTS_REQUIRE_APPROVAL=True):
            self.client.post(reverse("comments:add"), {"article_id": self.article.pk, "body": "Wait"})
        comment = Comment.objects.get()
        self.assertFalse(comment.approved)
        self.assertFalse(Notification.objects.exists())
