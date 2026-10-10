import logging
import os
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import stripe
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.charities.models import Charity
from apps.charities.services import charity_selection_for_period
from apps.payments.models import (
    Donation,
    FundingAllocation,
    StripeCustomer,
    StripeWebhookEvent,
    SubscriptionInvoice,
)
from apps.payments.stripe_utils import get_stripe_test_secret_key
from apps.subscriptions.models import Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)


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
    first_item = items[0] if items else {}
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

    period_start = _field(subscription_data, 'current_period_start')
    period_end = _field(subscription_data, 'current_period_end')
    return Subscription.objects.update_or_create(
        stripe_subscription_id=_field(subscription_data, 'id'),
        defaults={
            'user': user,
            'plan': plan,
            'status': status_value,
            'current_period_start': _as_datetime(
                period_start if period_start is not None else _field(first_item, 'current_period_start')
            ),
            'current_period_end': _as_datetime(
                period_end if period_end is not None else _field(first_item, 'current_period_end')
            ),
            'cancel_at_period_end': bool(_field(subscription_data, 'cancel_at_period_end', False)),
            'canceled_at': _as_datetime(_field(subscription_data, 'canceled_at')),
            'ended_at': _as_datetime(_field(subscription_data, 'ended_at')),
        },
    )[0]


def _allocate_charity_contribution(invoice):
    effective_at = invoice.period_start or invoice.paid_at
    selection = charity_selection_for_period(
        invoice.subscription.user_id,
        effective_at,
    )
    if selection is None:
        return

    amount_minor = invoice.amount_minor * selection.contribution_bps // 10000
    if amount_minor <= 0:
        return
    idempotency_key = uuid5(
        NAMESPACE_URL,
        f'invoice-charity-allocation:{invoice.pk}:{selection.pk}',
    )
    allocation = FundingAllocation.objects.select_for_update().filter(
        idempotency_key=idempotency_key,
    ).first()
    if allocation is None:
        FundingAllocation.objects.create(
            invoice=invoice,
            charity_selection=selection,
            allocation_type=FundingAllocation.Type.CHARITY,
            amount_minor=amount_minor,
            currency=invoice.currency,
            idempotency_key=idempotency_key,
        )
        return
    if (
        allocation.invoice.pk != invoice.pk
        or allocation.charity_selection is None
        or allocation.charity_selection.pk != selection.pk
        or allocation.allocation_type != FundingAllocation.Type.CHARITY
        or allocation.amount_minor != amount_minor
        or allocation.currency != invoice.currency
    ):
        raise ValueError('An existing charity allocation conflicts with this invoice.')


def _process_invoice(event_type, invoice_data):
    subscription_value = _field(invoice_data, 'subscription')
    if subscription_value is None:
        parent = _field(invoice_data, 'parent', {})
        subscription_details = _field(parent, 'subscription_details', {})
        subscription_value = _field(subscription_details, 'subscription')
    subscription_id = _field(subscription_value, 'id', subscription_value)
    subscription = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
    if subscription is None:
        raise ValueError('Invoice arrived before its subscription was recorded.')

    paid = event_type == 'invoice.paid'
    status_value = SubscriptionInvoice.Status.PAID if paid else SubscriptionInvoice.Status.OPEN
    period_start = _field(invoice_data, 'period_start')
    period_end = _field(invoice_data, 'period_end')
    if period_start is None or period_end is None or period_end <= period_start:
        lines = _field(_field(invoice_data, 'lines', {}), 'data', [])
        first_line_period = _field(lines[0], 'period', {}) if lines else {}
        period_start = _field(first_line_period, 'start', period_start)
        period_end = _field(first_line_period, 'end', period_end)
    invoice = SubscriptionInvoice.objects.update_or_create(
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
    )[0]
    if paid:
        _allocate_charity_contribution(invoice)
    if event_type == 'invoice.payment_failed' and subscription.status == Subscription.Status.ACTIVE:
        subscription.status = Subscription.Status.PAST_DUE
        subscription.save(update_fields=('status', 'updated_at'))


def _process_donation_checkout(event_type, session_data):
    donation_id = _field(_field(session_data, 'metadata', {}), 'donation_id')
    if not donation_id:
        return
    donation = Donation.objects.select_for_update().filter(pk=donation_id).first()
    if donation is None:
        raise ValueError('Checkout session does not match a donation.')
    session_id = _field(session_data, 'id')
    if donation.stripe_checkout_session_id and donation.stripe_checkout_session_id != session_id:
        raise ValueError('Checkout session does not match the recorded donation.')

    if event_type == 'checkout.session.expired':
        if donation.status == Donation.Status.PENDING:
            donation.status = Donation.Status.FAILED
            donation.save(update_fields=('status', 'updated_at'))
        return

    if event_type == 'checkout.session.async_payment_failed':
        donation.status = Donation.Status.FAILED
        donation.save(update_fields=('status', 'updated_at'))
        return

    if _field(session_data, 'payment_status') != 'paid':
        return
    amount_total = _field(session_data, 'amount_total')
    currency = (_field(session_data, 'currency', '') or '').upper()
    payment_intent = _field(session_data, 'payment_intent')
    payment_intent_id = _field(payment_intent, 'id', payment_intent)
    if (
        amount_total != donation.amount_minor
        or currency != donation.currency
        or not payment_intent_id
    ):
        raise ValueError('Paid donation does not match its recorded amount and currency.')
    if (
        donation.stripe_payment_intent_id
        and donation.stripe_payment_intent_id != payment_intent_id
    ):
        raise ValueError('Payment intent does not match the recorded donation.')
    donation.stripe_checkout_session_id = session_id
    donation.stripe_payment_intent_id = payment_intent_id
    donation.status = Donation.Status.SUCCEEDED
    donation.paid_at = donation.paid_at or timezone.now()
    donation.save(update_fields=(
        'stripe_checkout_session_id',
        'stripe_payment_intent_id',
        'status',
        'paid_at',
        'updated_at',
    ))


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
            elif event_type in {
                'checkout.session.completed',
                'checkout.session.async_payment_succeeded',
                'checkout.session.async_payment_failed',
                'checkout.session.expired',
            }:
                if _field(data, 'mode') != 'subscription':
                    _process_donation_checkout(event_type, data)
            elif event_type == 'charge.refunded':
                payment_intent = _field(data, 'payment_intent')
                payment_intent_id = _field(payment_intent, 'id', payment_intent)
                donation = Donation.objects.select_for_update().filter(
                    stripe_payment_intent_id=payment_intent_id,
                ).first()
                if donation and _field(data, 'amount_refunded', 0) >= donation.amount_minor:
                    donation.status = Donation.Status.REFUNDED
                    donation.save(update_fields=('status', 'updated_at'))
        except Exception as error:
            logger.exception('Stripe webhook processing failed for event type %s.', event_type)
            record.status = StripeWebhookEvent.Status.FAILED
            record.last_error = type(error).__name__
            record.save(update_fields=('status', 'last_error', 'updated_at'))
            return Response({'detail': 'Webhook processing failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        record.status = StripeWebhookEvent.Status.SUCCEEDED
        record.processed_at = timezone.now()
        record.save(update_fields=('status', 'processed_at', 'updated_at'))
        return Response({'received': True})


class DonationCheckoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        charity = get_object_or_404(Charity, pk=request.data.get('charity_id'), is_active=True)
        amount_minor = request.data.get('amount_minor')
        if (
            isinstance(amount_minor, bool)
            or not isinstance(amount_minor, int)
            or not 100 <= amount_minor <= 1_000_000
        ):
            return Response(
                {'amount_minor': 'Enter a donation from 100 to 1,000,000 minor units.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        currency = os.getenv('DONATION_CURRENCY', 'USD').strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            return Response(
                {'detail': 'The donation currency is not configured correctly.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        secret_key = get_stripe_test_secret_key()
        if not secret_key:
            return Response(
                {'code': 'stripe_not_configured', 'detail': 'Donations are not available right now.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        donation = Donation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            charity=charity,
            amount_minor=amount_minor,
            currency=currency,
        )
        frontend_url = os.getenv('FRONTEND_BASE_URL', 'http://127.0.0.1:3000').rstrip('/')
        try:
            session = stripe.checkout.Session.create(
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'unit_amount': amount_minor,
                        'product_data': {'name': f'Donation to {charity.name}'},
                    },
                    'quantity': 1,
                }],
                metadata={
                    'donation_id': str(donation.pk),
                    'charity_id': str(charity.pk),
                },
                payment_intent_data={
                    'metadata': {
                        'donation_id': str(donation.pk),
                        'charity_id': str(charity.pk),
                    },
                },
                success_url=f'{frontend_url}/donate?status=success',
                cancel_url=f'{frontend_url}/donate?status=cancelled',
                api_key=secret_key,
                idempotency_key=f'digital-heroes-donation-{donation.pk}',
            )
        except stripe.StripeError:
            logger.exception('Stripe donation checkout session could not be created.')
            donation.status = Donation.Status.FAILED
            donation.save(update_fields=('status', 'updated_at'))
            return Response(
                {'detail': 'Donation checkout is temporarily unavailable. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        donation.stripe_checkout_session_id = session.id
        donation.save(update_fields=('stripe_checkout_session_id', 'updated_at'))
        return Response({'checkout_url': session.url}, status=status.HTTP_201_CREATED)


class DonationConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        currency = os.getenv('DONATION_CURRENCY', 'USD').strip().upper()
        stripe_configured = get_stripe_test_secret_key()
        return Response({
            'currency': currency,
            'minimum_minor': 100,
            'maximum_minor': 1_000_000,
            'checkout_available': (
                len(currency) == 3
                and currency.isalpha()
                and bool(stripe_configured)
            ),
        })
