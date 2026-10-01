from django.conf import settings
from django.db import models
from django.utils import timezone

from articles.models import Article


class DailyStats(models.Model):
    """
    Track daily statistics for articles and user engagement.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_stats")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, null=True, blank=True, related_name="daily_stats")

    date = models.DateField(default=timezone.localdate)
    views = models.PositiveIntegerField(default=0)
    reads = models.PositiveIntegerField(default=0)  # completed reads
    likes = models.PositiveIntegerField(default=0)
    followers_gained = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "article", "date")
        ordering = ["-date"]
        indexes = [models.Index(fields=["user", "-date"])]

    def __str__(self):
        return f"{self.user} - {self.date}"


class UserStats(models.Model):
    """
    Aggregate user statistics (cached/denormalized).
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_stats")

    total_views = models.PositiveIntegerField(default=0)
    total_reads = models.PositiveIntegerField(default=0)
    total_followers = models.PositiveIntegerField(default=0)
    total_subscribers = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.user}"