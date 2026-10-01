from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from notifications.models import Notification, UserFollowing
from .models import Article, Tag
from .sanitizers import sanitize_html


class SanitizerTests(TestCase):
    def test_strips_scripts_and_event_handlers(self):
        html = '<p onclick="x()">Hi<script>alert(1)</script><img src="x" onerror="alert(1)"></p>'
        clean = sanitize_html(html)
        self.assertNotIn("<script", clean)
        self.assertNotIn("onerror", clean)
        self.assertNotIn("onclick", clean)
        self.assertIn("Hi", clean)

    def test_strips_javascript_links(self):
        self.assertNotIn("javascript:", sanitize_html('<a href="javascript:alert(1)">x</a>'))

    def test_keeps_quill_formatting(self):
        html = '<p class="ql-align-center"><strong>Bold</strong> <a href="https://example.com">link</a></p>'
        clean = sanitize_html(html)
        self.assertIn('class="ql-align-center"', clean)
        self.assertIn("<strong>Bold</strong>", clean)
        self.assertIn('href="https://example.com"', clean)

    def test_article_body_is_sanitized_on_save(self):
        author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")
        article = Article.objects.create(author=author, title="T", body="<p>ok</p><script>bad()</script>")
        self.assertEqual(article.body, "<p>ok</p>")


class ArticleViewTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")
        self.reader = CustomUser.objects.create_user("reader", "r@example.com", "pass12345!")

    def article_data(self, **overrides):
        data = {
            "title": "My first story",
            "excerpt": "",
            "body": "<p>Hello world</p>",
            "status": "published",
            "tags": "Django, Python, django",
        }
        data.update(overrides)
        return data

    def test_create_article_saves_tags(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse("articles:create"), self.article_data())
        article = Article.objects.get()
        self.assertRedirects(response, article.get_absolute_url())
        self.assertEqual(article.author, self.author)
        # duplicate "django" (case-insensitive) is ignored
        self.assertEqual(sorted(article.tags.values_list("name", flat=True)), ["Django", "Python"])

    def test_edit_article_updates_tags(self):
        self.client.force_login(self.author)
        self.client.post(reverse("articles:create"), self.article_data())
        article = Article.objects.get()

        response = self.client.post(
            reverse("articles:edit", args=[article.slug]),
            self.article_data(title="Changed", tags="web"),
        )
        self.assertEqual(response.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.title, "Changed")
        self.assertEqual(list(article.tags.values_list("name", flat=True)), ["web"])

    def test_empty_quill_body_is_rejected(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse("articles:create"), self.article_data(body="<p><br></p>"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Article.objects.exists())

    def test_only_author_can_edit(self):
        article = Article.objects.create(author=self.author, title="T", body="<p>x</p>", status="published")
        self.client.force_login(self.reader)
        response = self.client.get(reverse("articles:edit", args=[article.slug]))
        self.assertEqual(response.status_code, 403)

    def test_drafts_are_hidden_from_other_users(self):
        draft = Article.objects.create(author=self.author, title="Secret", body="<p>x</p>", status="draft")
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)

        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)

        self.client.force_login(self.author)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 200)

    def test_member_only_requires_following(self):
        article = Article.objects.create(
            author=self.author, title="Members", body="<p>x</p>", status="published", is_member_only=True
        )
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(article.get_absolute_url()).status_code, 404)

        UserFollowing.objects.create(follower=self.reader, following=self.author)
        self.assertEqual(self.client.get(article.get_absolute_url()).status_code, 200)

    def test_view_counted_once_per_session(self):
        article = Article.objects.create(author=self.author, title="T", body="<p>x</p>", status="published")
        self.client.get(article.get_absolute_url())
        self.client.get(article.get_absolute_url())
        article.refresh_from_db()
        self.assertEqual(article.views_count, 1)

    def test_publishing_notifies_followers(self):
        UserFollowing.objects.create(follower=self.reader, following=self.author)
        self.client.force_login(self.author)
        self.client.post(reverse("articles:create"), self.article_data())
        self.assertTrue(
            Notification.objects.filter(recipient=self.reader, notification_type="new_article").exists()
        )

    def test_list_search_and_tag_filter(self):
        a1 = Article.objects.create(author=self.author, title="Django tips", body="<p>x</p>", status="published")
        Article.objects.create(author=self.author, title="Cooking", body="<p>y</p>", status="published")
        a1.tags.add(Tag.objects.create(name="Web"))

        response = self.client.get(reverse("articles:list"), {"q": "django"})
        self.assertEqual(list(response.context["object_list"]), [a1])

        response = self.client.get(reverse("articles:list"), {"tag": "web"})
        self.assertEqual(list(response.context["object_list"]), [a1])

    def test_home_and_list_render(self):
        Article.objects.create(author=self.author, title="Hello", body="<p>x</p>", status="published")
        self.assertContains(self.client.get(reverse("core:home")), "Hello")
        self.assertContains(self.client.get(reverse("articles:list")), "Hello")


class SearchTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user("writer", "w@example.com", "pass12345!")

    def test_body_text_has_no_html(self):
        article = Article.objects.create(
            author=self.author, title="T", body="<p>Hello&nbsp;<strong>world</strong></p><p>Again</p>"
        )
        self.assertEqual(article.body_text, "Hello world Again")

    def test_search_does_not_match_html_markup(self):
        Article.objects.create(
            author=self.author, title="Plain", status="published",
            body='<p class="ql-align-center"><strong>Python</strong> tips</p>',
        )
        self.assertEqual(Article.objects.search("strong").count(), 0)
        self.assertEqual(Article.objects.search("ql-align").count(), 0)
        self.assertEqual(Article.objects.search("python").count(), 1)
