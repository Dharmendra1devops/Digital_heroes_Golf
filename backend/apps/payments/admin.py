from django.contrib import admin

from apps.payments.models import (
    Donation,
    FundingAllocation,
    StripeCustomer,
    StripeWebhookEvent,
    SubscriptionInvoice,
)


@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'stripe_customer_id', 'created_at')
    search_fields = ('user__email', 'stripe_customer_id')
    readonly_fields = ('user', 'stripe_customer_id', 'created_at', 'updated_at')


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = ('stripe_invoice_id', 'subscription', 'status', 'amount_minor', 'currency', 'paid_at')
    list_filter = ('status', 'currency')
    search_fields = ('stripe_invoice_id', 'subscription__user__email')
    readonly_fields = tuple(field.name for field in SubscriptionInvoice._meta.fields)


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('stripe_event_id', 'event_type', 'status', 'received_at', 'processed_at')
    list_filter = ('status', 'event_type')
    search_fields = ('stripe_event_id', 'event_type')
    readonly_fields = tuple(field.name for field in StripeWebhookEvent._meta.fields)


@admin.register(FundingAllocation)
class FundingAllocationAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'allocation_type', 'amount_minor', 'currency', 'draw', 'created_at')
    list_filter = ('allocation_type', 'currency')
    readonly_fields = tuple(field.name for field in FundingAllocation._meta.fields)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('charity', 'user', 'status', 'amount_minor', 'currency', 'paid_at')
    list_filter = ('status', 'currency', 'charity')
    search_fields = ('user__email', 'stripe_payment_intent_id')
    readonly_fields = tuple(field.name for field in Donation._meta.fields)
