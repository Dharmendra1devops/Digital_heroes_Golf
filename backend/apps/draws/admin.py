from django.contrib import admin

from apps.draws.models import (
    Draw,
    DrawConfiguration,
    DrawEntry,
    DrawPrizeTierConfiguration,
    DrawRun,
    DrawTierPool,
)


class DrawPrizeTierInline(admin.TabularInline):
    model = DrawPrizeTierConfiguration
    extra = 0


class DrawTierPoolInline(admin.TabularInline):
    model = DrawTierPool
    extra = 0
    readonly_fields = tuple(field.name for field in DrawTierPool._meta.fields)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DrawConfiguration)
class DrawConfigurationAdmin(admin.ModelAdmin):
    list_display = ('version', 'mode', 'candidate_min', 'candidate_max', 'number_count', 'prize_pool_contribution_bps')
    list_filter = ('mode',)
    inlines = (DrawPrizeTierInline,)


@admin.register(Draw)
class DrawAdmin(admin.ModelAdmin):
    list_display = ('scheduled_at', 'eligibility_cutoff', 'status', 'configuration')
    list_filter = ('status', 'configuration__mode')
    ordering = ('-scheduled_at',)
    inlines = (DrawTierPoolInline,)
    readonly_fields = ('configuration_snapshot', 'published_at', 'created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj and obj.status == Draw.Status.PUBLISHED:
            return (*fields, 'configuration', 'scheduled_at', 'eligibility_cutoff', 'status')
        return fields

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'status':
            kwargs['choices'] = [
                (value, label)
                for value, label in Draw.Status.choices
                if value != Draw.Status.PUBLISHED
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)


@admin.register(DrawRun)
class DrawRunAdmin(admin.ModelAdmin):
    list_display = ('draw', 'run_number', 'run_type', 'algorithm_version', 'is_published', 'created_at')
    list_filter = ('run_type', 'is_published')
    readonly_fields = ('draw', 'run_number', 'run_type', 'algorithm_version', 'input_hash', 'input_snapshot', 'result_snapshot', 'audit_metadata', 'is_published', 'created_at', 'updated_at')


@admin.register(DrawEntry)
class DrawEntryAdmin(admin.ModelAdmin):
    list_display = ('draw', 'user', 'subscription', 'eligible_at')
    search_fields = ('user__email',)
    readonly_fields = ('draw', 'user', 'subscription', 'eligible_at', 'subscription_snapshot', 'score_snapshot', 'created_at', 'updated_at')
