from django.contrib import admin

from .models import DailyStats


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "date", "views", "reads", "likes", "followers_gained")
    list_filter = ("date",)
    search_fields = ("user__username", "article__title")
    list_select_related = ("user", "article")
    readonly_fields = ("date",)
