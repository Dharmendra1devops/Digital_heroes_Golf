from django.contrib import admin

from apps.scores.models import GolfScore


@admin.register(GolfScore)
class GolfScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'score_date', 'score', 'created_at')
    list_filter = ('score_date',)
    search_fields = ('user__username', 'user__email')
    ordering = ('-score_date',)
    readonly_fields = ('created_at', 'updated_at')
