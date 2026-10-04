from django.conf import settings
from django.db import models

from articles.models import Article


class CommentQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(approved=True)


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    body = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    created_at = models.DateTimeField(auto_now_add=True)
    # Hidden comments (approved=False) and their replies are not shown on the site.
    # With COMMENTS_REQUIRE_APPROVAL=True new comments wait for a moderator.
    approved = models.BooleanField(default=True, db_index=True)

    objects = CommentQuerySet.as_manager()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.article}"

    @classmethod
    def tree_for(cls, article):
        """
        Approved comments of an article as a tree, loaded with a single query.
        Each comment gets a `replies` list. Replies to hidden comments are hidden too.
        """
        comments = list(cls.objects.approved().filter(article=article).select_related("author"))
        by_id = {c.pk: c for c in comments}
        roots = []
        for c in comments:
            c.replies = []
        for c in comments:
            if c.parent_id is None:
                roots.append(c)
            elif c.parent_id in by_id:
                by_id[c.parent_id].replies.append(c)
        return roots
