from django.urls import path

from apps.payments.views import DonationCheckoutView, DonationConfigView, StripeWebhookView

app_name = 'payments'

urlpatterns = [
    path('donations/config/', DonationConfigView.as_view(), name='donation-config'),
    path('donations/checkout/', DonationCheckoutView.as_view(), name='donation-checkout'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
