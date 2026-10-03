from django.contrib import admin

from apps.accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('email', 'display_name', 'user', 'created_at')
    search_fields = ('email', 'display_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
