from django.urls import path
from . import views

app_name = "interactions"

urlpatterns = [
    path("like-toggle/<int:article_id>/", views.toggle_like, name="like-toggle"),
    path("bookmark-toggle/<int:article_id>/", views.toggle_bookmark, name="bookmark-toggle"),
    path("library/", views.library_view, name="library"),

    # lists
    path("lists/", views.lists_view, name="lists"),
    path("lists/<int:list_id>/", views.reading_list_detail, name="reading-list-detail"),
    path("add-to-list/", views.add_to_list, name="add-to-list"),
    path("remove-from-list/", views.remove_from_list, name="remove-from-list"),
]