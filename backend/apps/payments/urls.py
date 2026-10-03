from django.urls import path

from apps.payments.views import StripeWebhookView

app_name = 'payments'

urlpatterns = [
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
