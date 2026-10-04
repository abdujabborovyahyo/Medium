from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from interactions.models import ArticleLike
from notifications.models import UserFollowing
from .models import DailyStats


@receiver(post_save, sender=ArticleLike)
def like_added(sender, instance, created, **kwargs):
    if created:
        DailyStats.change(
            "likes", user_id=instance.article.author_id, article_id=instance.article_id
        )


@receiver(post_delete, sender=ArticleLike)
def like_removed(sender, instance, **kwargs):
    # Only today's counter is corrected; older days stay as history.
    DailyStats.change(
        "likes", user_id=instance.article.author_id, article_id=instance.article_id, amount=-1
    )


@receiver(post_save, sender=UserFollowing)
def follower_added(sender, instance, created, **kwargs):
    if created:
        DailyStats.change("followers_gained", user_id=instance.following_id)


@receiver(post_delete, sender=UserFollowing)
def follower_removed(sender, instance, **kwargs):
    DailyStats.change("followers_gained", user_id=instance.following_id, amount=-1)
