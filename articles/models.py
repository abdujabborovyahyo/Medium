import html
import re

from django.conf import settings
from django.db import connection, models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify

from .sanitizers import sanitize_html


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:50] or "tag"
            slug = base
            counter = 1
            while Tag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


def html_to_text(value):
    """Plain text version of the article HTML (used for search and previews)."""
    text = html.unescape(strip_tags(re.sub(r"<(br|/p|/h\d|/li|/blockquote)[^>]*>", " ", value or "")))
    return re.sub(r"\s+", " ", text).strip()


class ArticleQuerySet(models.QuerySet):
    def search(self, query):
        """
        PostgreSQL: real full-text search ranked by relevance (title > excerpt > body).
        Other databases (SQLite in development): simple case-insensitive matching.
        """
        query = (query or "").strip()
        if not query:
            return self
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

            vector = (
                SearchVector("title", weight="A")
                + SearchVector("excerpt", weight="B")
                + SearchVector("body_text", weight="C")
            )
            search_query = SearchQuery(query, search_type="websearch")
            # Filter with the @@ match operator; rank only orders the matches
            # (ts_rank can be slightly above 0 even for rows that don't match).
            return (
                self.annotate(search=vector, rank=SearchRank(vector, search_query))
                .filter(search=search_query)
                .order_by("-rank", "-published_at")
            )
        return self.filter(
            Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(body_text__icontains=query)
        )

    def published(self):
        return self.filter(status=Article.Status.PUBLISHED)

    def visible_to(self, user):
        """Published articles + the user's own drafts."""
        if user.is_authenticated:
            return self.filter(Q(status=Article.Status.PUBLISHED) | Q(author=user))
        return self.published()


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="articles")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    # Sanitized HTML produced by the Quill editor (see sanitizers.py)
    body = models.TextField()
    # Plain text copy of `body` (no HTML tags), filled automatically in save()
    body_text = models.TextField(blank=True, editable=False)
    excerpt = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")

    is_member_only = models.BooleanField(default=False, help_text="Only followers can read this article")
    cover_image = models.ImageField(upload_to="article_covers/", blank=True, null=True)

    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["-published_at", "status"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        self.body = sanitize_html(self.body)
        self.body_text = html_to_text(self.body)
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.title)[:200] or "article"
        slug = base
        counter = 1
        while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def get_absolute_url(self):
        return reverse("articles:detail", kwargs={"slug": self.slug})

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def summary(self):
        """Excerpt, or the beginning of the body as plain text."""
        return self.excerpt or self.body_text

    def can_view(self, user):
        """Check if a user can read this article."""
        if user and user.is_authenticated and user == self.author:
            return True
        if not self.is_published:
            return False
        if not self.is_member_only:
            return True
        if not user or not user.is_authenticated:
            return False
        return self.author.followers.filter(follower=user).exists()
