from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("short_body", "author", "article", "created_at", "approved")
    list_filter = ("approved", "created_at")
    list_editable = ("approved",)
    search_fields = ("body", "author__username", "article__title")
    list_select_related = ("author", "article")
    raw_id_fields = ("article", "author", "parent")
    actions = ("approve", "hide")

    @admin.display(description="Comment")
    def short_body(self, obj):
        return obj.body[:60]

    @admin.action(description="Approve selected comments")
    def approve(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"{updated} comment(s) approved.")

    @admin.action(description="Hide selected comments")
    def hide(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f"{updated} comment(s) hidden.")
