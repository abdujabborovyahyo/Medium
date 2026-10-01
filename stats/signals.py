from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from notifications.models import ReadingHistory
from .models import DailyStats


@receiver(post_save, sender=ReadingHistory)
def track_article_view(sender, instance, created, **kwargs):
    """
    Count a view for the article's author when a user opens an article
    for the first time (ReadingHistory row created).
    """
    if not created:
        return
    daily_stat, _ = DailyStats.objects.get_or_create(
        user_id=instance.article.author_id,
        article_id=instance.article_id,
        date=timezone.localdate(),
    )
    # F() expression: atomic increment, no lost updates under concurrent requests
    DailyStats.objects.filter(pk=daily_stat.pk).update(views=F("views") + 1)
