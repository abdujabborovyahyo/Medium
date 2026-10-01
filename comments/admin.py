from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "article", "created_at", "approved")
    list_filter = ("approved", "created_at")
    search_fields = ("body", "author__username", "article__title")
    list_select_related = ("author", "article")
    raw_id_fields = ("article", "author", "parent")
