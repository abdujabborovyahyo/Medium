from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from .models import Notification, ReadingHistory, UserFollowing
from django.contrib.auth import get_user_model
from django.utils.http import url_has_allowed_host_and_scheme

User = get_user_model()


@login_required
@require_http_methods(["POST"])
def follow_user(request, user_id):
    """
    Follow or unfollow a user. Send notification and Django message.
    Supports both AJAX (JSON) and form POST.
    """
    user_to_follow = get_object_or_404(User, pk=user_id)

    if user_to_follow == request.user:
        error_msg = "You cannot follow yourself."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"error": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('core:home')

    # Toggle follow
    following_rel, created = UserFollowing.objects.get_or_create(
        follower=request.user,
        following=user_to_follow
    )

    if not created:
        # User was already following, so unfollow
        following_rel.delete()
        is_following = False
        msg = f"You unfollowed {user_to_follow.username}."
    else:
        # New follow
        is_following = True
        msg = f"You are now following {user_to_follow.username}."

        # Notify the followed user, but don't spam them on follow/unfollow/follow toggling
        already_notified = Notification.objects.filter(
            recipient=user_to_follow, sender=request.user, notification_type=Notification.Type.FOLLOW
        ).exists()
        if not already_notified:
            Notification.objects.create(
                recipient=user_to_follow,
                sender=request.user,
                notification_type=Notification.Type.FOLLOW,
                title=f"{request.user.username} started following you",
            )

    # Handle AJAX requests (return JSON)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "is_following": is_following,
            "followers_count": user_to_follow.followers.count(),
            "message": msg
        })

    # Handle regular form submissions (redirect with message)
    messages.success(request, msg)
    # Only redirect back to our own site (the Referer header can be anything)
    referer = request.META.get("HTTP_REFERER", "")
    if url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(referer)
    return redirect("accounts:profile", username=user_to_follow.username)


@login_required
def notifications_list(request):
    """
    Show all notifications for the logged-in user.
    """
    notifications = request.user.notifications.select_related("sender", "article")[:100]
    unread_count = request.user.notifications.filter(is_read=False).count()
    return render(request, "notifications/notifications_list.html", {
        "notifications": notifications,
        "unread_count": unread_count
    })


@login_required
@require_POST
def mark_as_read(request, notification_id):
    """
    Mark a single notification as read.
    """
    notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    notification.mark_as_read()
    return JsonResponse({"success": True, "is_read": notification.is_read})


@login_required
@require_POST
def mark_all_as_read(request):
    """
    Mark all notifications as read.
    """
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({"success": True})


@login_required
def unread_count(request):
    """
    AJAX endpoint: return count of unread notifications for badge.
    """
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"unread_count": count})


@login_required
def reading_history(request):
    """
    Show user's reading history (articles they viewed).
    """
    history = request.user.reading_history.select_related("article__author").all()
    return render(request, "notifications/reading_history.html", {"history": history})