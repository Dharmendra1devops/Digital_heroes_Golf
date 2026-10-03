import os
from datetime import UTC, datetime

import stripe
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import StripeCustomer, StripeWebhookEvent, SubscriptionInvoice
from apps.subscriptions.models import Subscription, SubscriptionPlan


def _field(value, name, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _as_datetime(timestamp):
    return datetime.fromtimestamp(timestamp, tz=UTC) if timestamp else None


def _user_for_customer(customer_id, metadata):
    mapping = StripeCustomer.objects.select_related('user').filter(stripe_customer_id=customer_id).first()
    if mapping:
        return mapping.user
    user_id = _field(metadata, 'user_id')
    if user_id:
        user = get_user_model().objects.get(pk=user_id)
        StripeCustomer.objects.get_or_create(user=user, defaults={'stripe_customer_id': customer_id})
        return user
    raise ValueError('Stripe customer is not linked to an account.')


def _process_subscription(event_type, subscription_data):
    customer_id = _field(subscription_data, 'customer')
    metadata = _field(subscription_data, 'metadata', {})
    user = _user_for_customer(customer_id, metadata)
    items = _field(_field(subscription_data, 'items', {}), 'data', [])
    price = _field(items[0], 'price', {}) if items else {}
    price_id = _field(price, 'id')
    plan_id = _field(metadata, 'plan_id')
    plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
    if plan is None and plan_id:
        plan = SubscriptionPlan.objects.filter(pk=plan_id).first()
    if plan is None:
        raise ValueError('Stripe subscription does not match a configured plan.')

    status_value = _field(subscription_data, 'status', Subscription.Status.INCOMPLETE)
    if event_type == 'customer.subscription.deleted':
        status_value = Subscription.Status.CANCELED
    allowed_statuses = {choice for choice, _label in Subscription.Status.choices}
    if status_value not in allowed_statuses:
        status_value = Subscription.Status.INCOMPLETE

    return Subscription.objects.update_or_create(
        stripe_subscription_id=_field(subscription_data, 'id'),
        defaults={
            'user': user,
            'plan': plan,
            'status': status_value,
            'current_period_start': _as_datetime(_field(subscription_data, 'current_period_start')),
            'current_period_end': _as_datetime(_field(subscription_data, 'current_period_end')),
            'cancel_at_period_end': bool(_field(subscription_data, 'cancel_at_period_end', False)),
            'canceled_at': _as_datetime(_field(subscription_data, 'canceled_at')),
            'ended_at': _as_datetime(_field(subscription_data, 'ended_at')),
        },
    )[0]


def _process_invoice(event_type, invoice_data):
    subscription_value = _field(invoice_data, 'subscription')
    subscription_id = _field(subscription_value, 'id', subscription_value)
    subscription = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
    if subscription is None:
        raise ValueError('Invoice arrived before its subscription was recorded.')

    paid = event_type == 'invoice.paid'
    status_value = SubscriptionInvoice.Status.PAID if paid else SubscriptionInvoice.Status.OPEN
    period_start = _field(invoice_data, 'period_start')
    period_end = _field(invoice_data, 'period_end')
    SubscriptionInvoice.objects.update_or_create(
        stripe_invoice_id=_field(invoice_data, 'id'),
        defaults={
            'subscription': subscription,
            'amount_minor': max(0, _field(invoice_data, 'amount_paid' if paid else 'amount_due', 0)),
            'currency': (_field(invoice_data, 'currency', subscription.plan.currency) or subscription.plan.currency).upper(),
            'status': status_value,
            'period_start': _as_datetime(period_start),
            'period_end': _as_datetime(period_end),
            'paid_at': timezone.now() if paid else None,
        },
    )
    if event_type == 'invoice.payment_failed' and subscription.status == Subscription.Status.ACTIVE:
        subscription.status = Subscription.Status.PAST_DUE
        subscription.save(update_fields=('status', 'updated_at'))


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
        if not webhook_secret or webhook_secret == 'whsec_your_secret':
            return Response({'detail': 'Stripe webhooks are not configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            event = stripe.Webhook.construct_event(
                request.body,
                request.headers.get('Stripe-Signature', ''),
                webhook_secret,
            )
        except (ValueError, stripe.SignatureVerificationError):
            return Response({'detail': 'Invalid Stripe webhook signature.'}, status=status.HTTP_400_BAD_REQUEST)

        event_id = _field(event, 'id')
        event_type = _field(event, 'type', '')
        record, created = StripeWebhookEvent.objects.get_or_create(
            stripe_event_id=event_id,
            defaults={
                'event_type': event_type,
                'status': StripeWebhookEvent.Status.PROCESSING,
            },
        )
        record = StripeWebhookEvent.objects.select_for_update().get(pk=record.pk)
        if not created and record.status == StripeWebhookEvent.Status.SUCCEEDED:
            return Response({'received': True, 'duplicate': True})

        try:
            data = _field(_field(event, 'data', {}), 'object', {})
            if event_type.startswith('customer.subscription.'):
                _process_subscription(event_type, data)
            elif event_type in {'invoice.paid', 'invoice.payment_failed'}:
                _process_invoice(event_type, data)
        except Exception as error:
            record.status = StripeWebhookEvent.Status.FAILED
            record.last_error = type(error).__name__
            record.save(update_fields=('status', 'last_error', 'updated_at'))
            return Response({'detail': 'Webhook processing failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        record.status = StripeWebhookEvent.Status.SUCCEEDED
        record.processed_at = timezone.now()
        record.save(update_fields=('status', 'processed_at', 'updated_at'))
        return Response({'received': True})
