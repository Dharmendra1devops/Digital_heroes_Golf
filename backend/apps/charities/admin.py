from django.contrib import admin

from apps.charities.models import Charity, CharityEvent, CharitySelection


class CharityEventInline(admin.TabularInline):
    model = CharityEvent
    extra = 0


@admin.register(Charity)
class CharityAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'is_featured', 'display_order')
    list_filter = ('is_active', 'is_featured')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (CharityEventInline,)


@admin.register(CharitySelection)
class CharitySelectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'charity', 'contribution_bps', 'effective_from', 'effective_to')
    list_filter = ('charity', 'effective_to')
    search_fields = ('user__email', 'charity__name')
    readonly_fields = ('created_at', 'updated_at')
