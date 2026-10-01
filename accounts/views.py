from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from notifications.models import UserFollowing
from .forms import CustomUserCreationForm, LoginForm, ProfileForm
from .models import CustomUser


def _safe_next_url(request, default="core:home"):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return default


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account was created.")
            return redirect(_safe_next_url(request))
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/signup.html", {"form": form, "next": request.GET.get("next", "")})


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def profile_view(request, username):
    user_obj = get_object_or_404(CustomUser, username=username)
    published_articles = user_obj.articles.published()

    is_following = False
    if request.user.is_authenticated and request.user != user_obj:
        is_following = UserFollowing.objects.filter(follower=request.user, following=user_obj).exists()

    stats = {
        "articles_count": published_articles.count(),
        "followers_count": user_obj.followers.count(),
        "bookmarks_count": user_obj.bookmarks.count(),
    }

    return render(request, "accounts/profile.html", {
        "profile_user": user_obj,
        "articles": published_articles,
        "stats": stats,
        "is_following": is_following,
    })


@login_required
def profile_edit(request, username):
    # Only the owner can edit their profile
    if request.user.username != username:
        return redirect("accounts:profile", username=request.user.username)

    # Work on a separate copy: an invalid form must not change request.user
    # (e.g. the username shown in the header) before it is saved.
    user = CustomUser.objects.get(pk=request.user.pk)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile", username=user.username)
    else:
        form = ProfileForm(instance=user)
    return render(request, "accounts/profile_edit.html", {"form": form})


@require_http_methods(["GET", "POST"])
@login_required
def logout_confirm(request):
    """
    Show confirmation page (GET). On POST, log the user out and redirect home.
    """
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect("core:home")
    return render(request, "accounts/logout_confirm.html")
