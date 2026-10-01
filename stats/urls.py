from django.urls import path

from . import views

app_name = "stats"

urlpatterns = [
    path("dashboard/", views.stats_view, name="dashboard"),
    path("audience/", views.audience_view, name="audience"),
    path("read/<int:article_id>/", views.record_read, name="record-read"),
]
