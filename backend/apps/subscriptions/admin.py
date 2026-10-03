from django.contrib import admin

from apps.subscriptions.models import Subscription, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('interval', 'amount_minor', 'currency', 'is_active', 'stripe_price_id')
    list_filter = ('interval', 'currency', 'is_active')
    search_fields = ('stripe_price_id',)
    ordering = ('amount_minor',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'current_period_end', 'cancel_at_period_end')
    list_filter = ('status', 'plan__interval', 'cancel_at_period_end')
    search_fields = ('user__email', 'stripe_subscription_id')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'current_period_end'
