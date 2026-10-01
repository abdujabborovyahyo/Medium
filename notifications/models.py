from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        NEW_ARTICLE = "new_article", "New Article"
        COMMENT = "comment", "Comment"
        REPLY = "reply", "Reply to Comment"
        LIKE = "like", "Article Liked"
        BOOKMARK = "bookmark", "Article Saved"
        FOLLOW = "follow", "New Follower"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications_sent"
    )
    notification_type = models.CharField(max_length=20, choices=Type.choices)

    # Generic content links (flexible)
    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "-created_at"])]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=["is_read"])

    def mark_as_unread(self):
        self.is_read = False
        self.save(update_fields=["is_read"])


class ReadingHistory(models.Model):
    """
    Track when a user views an article (for 'Reading history' tab in Library).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_history")
    article = models.ForeignKey("articles.Article", on_delete=models.CASCADE, related_name="read_by")
    viewed_at = models.DateTimeField(auto_now=True)  # auto_now: updated each view

    class Meta:
        unique_together = ("user", "article")
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"{self.user} read {self.article}"


class UserFollowing(models.Model):
    """
    Track which users follow which other users.
    """
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_user_following"),
            models.CheckConstraint(condition=~models.Q(follower=models.F("following")), name="prevent_self_follow"),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"