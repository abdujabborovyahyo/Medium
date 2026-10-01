from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    # Show a confirmation before logging out
    path("logout/", views.logout_confirm, name="logout"),
    # The actual logout could also be the POST on the same view above; no separate perform needed.
    path("profile/<str:username>/", views.profile_view, name="profile"),
    path("profile/<str:username>/edit/", views.profile_edit, name="profile_edit"),
]
