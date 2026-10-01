from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from articles.models import Article


class DailyStats(models.Model):
    """
    Daily counters for an author.

    - Rows with an article hold per-article numbers: views, reads, likes.
    - Rows without an article hold per-author numbers: followers_gained.
    """
    COUNTER_FIELDS = ("views", "reads", "likes", "followers_gained")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_stats")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, null=True, blank=True, related_name="daily_stats")

    date = models.DateField(default=timezone.localdate)
    views = models.PositiveIntegerField(default=0)
    reads = models.PositiveIntegerField(default=0)  # reader scrolled to the end of the article
    likes = models.PositiveIntegerField(default=0)
    followers_gained = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["user", "-date"])]
        constraints = [
            # NULL is never equal to NULL in SQL, so one unique_together on (user, article, date)
            # would allow many "article=NULL" rows per day. Two partial constraints fix that.
            models.UniqueConstraint(
                fields=["user", "article", "date"],
                condition=Q(article__isnull=False),
                name="unique_daily_article_stats",
            ),
            models.UniqueConstraint(
                fields=["user", "date"],
                condition=Q(article__isnull=True),
                name="unique_daily_user_stats",
            ),
        ]
        verbose_name_plural = "daily stats"

    def __str__(self):
        return f"{self.user} - {self.article or 'profile'} - {self.date}"

    @classmethod
    def change(cls, field, *, user_id, article_id=None, amount=1):
        """
        Atomically add `amount` to today's counter. Negative amounts never go below zero.
        """
        if field not in cls.COUNTER_FIELDS:
            raise ValueError(f"Unknown counter: {field}")
        today = timezone.localdate()
        if amount < 0:
            cls.objects.filter(
                user_id=user_id, article_id=article_id, date=today, **{f"{field}__gte": -amount}
            ).update(**{field: F(field) + amount})
            return
        row, _ = cls.objects.get_or_create(user_id=user_id, article_id=article_id, date=today)
        cls.objects.filter(pk=row.pk).update(**{field: F(field) + amount})
