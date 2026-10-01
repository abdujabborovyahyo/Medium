from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("articles/", include("articles.urls")),
    path("comments/", include("comments.urls")),
    path("interactions/", include("interactions.urls")),
    path("notifications/", include("notifications.urls")),
    path("stats/", include("stats.urls")),
    path("", include("core.urls")),
]

# Static files are served by WhiteNoise (see settings.MIDDLEWARE).
# Uploaded media: served by Django only when explicitly enabled.
if settings.SERVE_MEDIA:
    media_prefix = settings.MEDIA_URL.lstrip("/")
    urlpatterns += [
        re_path(rf"^{media_prefix}(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
