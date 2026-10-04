import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.charities.models import Charity, CharitySelection
from apps.payments.models import (
    Donation,
    FundingAllocation,
    StripeCustomer,
    StripeWebhookEvent,
    SubscriptionInvoice,
)
from apps.subscriptions.models import Subscription, SubscriptionPlan


class StripeWebhookTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='webhook-member',
            email='webhook@example.com',
        )
        self.plan = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.MONTHLY,
            amount_minor=1200,
            currency='USD',
            stripe_price_id='price_webhook_test',
        )
        self.charity = Charity.objects.create(slug='webhook-charity', name='Community Cause')
        StripeCustomer.objects.create(user=self.user, stripe_customer_id='cus_webhook_test')
        self.event = {
            'id': 'evt_subscription_created_test',
            'type': 'customer.subscription.created',
            'data': {
                'object': {
                    'id': 'sub_webhook_test',
                    'customer': 'cus_webhook_test',
                    'status': 'active',
                    'current_period_start': 1790899200,
                    'current_period_end': 1793491200,
                    'cancel_at_period_end': False,
                    'items': {'data': [{'price': {'id': 'price_webhook_test'}}]},
                    'metadata': {'user_id': str(self.user.pk), 'plan_id': str(self.plan.pk)},
                },
            },
        }

    @patch('apps.payments.views.stripe.Webhook.construct_event')
    def test_signed_subscription_event_updates_access_and_is_idempotent(self, construct_event):
        construct_event.return_value = self.event
        with patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
            first = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )
            second = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()['duplicate'])
        self.assertEqual(Subscription.objects.get(stripe_subscription_id='sub_webhook_test').status, 'active')
        self.assertEqual(StripeWebhookEvent.objects.get(stripe_event_id=self.event['id']).status, 'succeeded')
        self.assertEqual(construct_event.call_count, 2)

    def test_webhook_fails_closed_without_signing_secret(self):
        with patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': ''}):
            response = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(StripeWebhookEvent.objects.exists())

    @patch('apps.payments.views.stripe.Webhook.construct_event')
    def test_subscription_event_reads_period_from_subscription_item(self, construct_event):
        event = {
            **self.event,
            'data': {
                'object': {
                    **self.event['data']['object'],
                    'current_period_start': None,
                    'current_period_end': None,
                    'items': {
                        'data': [{
                            'price': {'id': 'price_webhook_test'},
                            'current_period_start': 1790899200,
                            'current_period_end': 1793491200,
                        }],
                    },
                },
            },
        }
        construct_event.return_value = event
        with patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
            response = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )

        subscription = Subscription.objects.get(stripe_subscription_id='sub_webhook_test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            subscription.current_period_start,
            timezone.datetime.fromtimestamp(1790899200, tz=timezone.UTC),
        )
        self.assertEqual(
            subscription.current_period_end,
            timezone.datetime.fromtimestamp(1793491200, tz=timezone.UTC),
        )

    @patch('apps.payments.views.stripe.Webhook.construct_event')
    def test_paid_invoice_reads_subscription_from_parent_details(self, construct_event):
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_webhook_test',
            status=Subscription.Status.ACTIVE,
        )
        event = {
            'id': 'evt_invoice_paid_nested_subscription_test',
            'type': 'invoice.paid',
            'data': {
                'object': {
                    'id': 'in_webhook_test',
                    'amount_paid': 1200,
                    'currency': 'usd',
                    'period_start': 1790899200,
                    'period_end': 1790899200,
                    'lines': {
                        'data': [{
                            'period': {'start': 1790899200, 'end': 1793491200},
                        }],
                    },
                    'parent': {
                        'type': 'subscription_details',
                        'subscription_details': {'subscription': 'sub_webhook_test'},
                    },
                },
            },
        }
        construct_event.return_value = event
        with patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
            response = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )

        invoice = SubscriptionInvoice.objects.get(stripe_invoice_id='in_webhook_test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(invoice.subscription.stripe_subscription_id, 'sub_webhook_test')
        self.assertEqual(invoice.status, SubscriptionInvoice.Status.PAID)
        self.assertEqual(invoice.amount_minor, 1200)
        self.assertEqual(
            invoice.period_start,
            timezone.datetime.fromtimestamp(1790899200, tz=timezone.UTC),
        )
        self.assertEqual(
            invoice.period_end,
            timezone.datetime.fromtimestamp(1793491200, tz=timezone.UTC),
        )

    @patch('apps.payments.views.stripe.Webhook.construct_event')
    def test_paid_invoice_allocates_selected_charity_share_for_the_invoice_period(self, construct_event):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_charity_funding_test',
            status=Subscription.Status.ACTIVE,
        )
        period_start = timezone.datetime.fromtimestamp(1790899200, tz=timezone.UTC)
        previous_charity = Charity.objects.create(slug='period-charity', name='Period Cause')
        later_charity = Charity.objects.create(slug='later-charity', name='Later Cause')
        previous_selection = CharitySelection.objects.create(
            user=self.user,
            charity=previous_charity,
            contribution_bps=2500,
            effective_from=period_start - timedelta(days=30),
            effective_to=period_start + timedelta(days=1),
        )
        CharitySelection.objects.create(
            user=self.user,
            charity=later_charity,
            contribution_bps=8000,
            effective_from=period_start + timedelta(days=1),
        )
        event = {
            'id': 'evt_charity_invoice_allocation_test',
            'type': 'invoice.paid',
            'data': {
                'object': {
                    'id': 'in_charity_allocation_test',
                    'amount_paid': 1200,
                    'currency': 'usd',
                    'period_start': 1790899200,
                    'period_end': 1793491200,
                    'subscription': subscription.stripe_subscription_id,
                },
            },
        }
        construct_event.return_value = event
        with patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
            first = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )
            duplicate = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )

        allocation = FundingAllocation.objects.get(
            invoice__stripe_invoice_id='in_charity_allocation_test',
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(duplicate.json()['duplicate'])
        self.assertEqual(FundingAllocation.objects.count(), 1)
        self.assertEqual(allocation.charity_selection, previous_selection)
        self.assertEqual(allocation.allocation_type, FundingAllocation.Type.CHARITY)
        self.assertEqual(allocation.amount_minor, 300)
        self.assertEqual(allocation.currency, 'USD')

    @patch('apps.payments.views.stripe.checkout.Session.create')
    def test_guest_can_start_a_separate_charity_donation_checkout(self, create_session):
        create_session.return_value = SimpleNamespace(
            id='cs_donation_test',
            url='https://checkout.stripe.test/session',
        )
        with patch.dict(os.environ, {
            'STRIPE_SECRET_KEY': 'sk_test_donation',
            'DONATION_CURRENCY': 'USD',
            'FRONTEND_BASE_URL': 'https://digitalheroes.example',
        }):
            response = self.client.post(
                '/api/payments/donations/checkout/',
                {'charity_id': str(self.charity.pk), 'amount_minor': 2500},
                content_type='application/json',
            )

        donation = Donation.objects.get()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.stripe.test/session')
        self.assertEqual(donation.user, None)
        self.assertEqual(donation.status, Donation.Status.PENDING)
        self.assertEqual(donation.amount_minor, 2500)
        self.assertEqual(donation.currency, 'USD')
        self.assertEqual(donation.stripe_checkout_session_id, 'cs_donation_test')
        self.assertEqual(Subscription.objects.count(), 0)
        self.assertEqual(create_session.call_args.kwargs['mode'], 'payment')

    @patch('apps.payments.views.stripe.checkout.Session.create')
    def test_donation_checkout_validates_amount_and_fails_closed_without_stripe(self, create_session):
        invalid = self.client.post(
            '/api/payments/donations/checkout/',
            {'charity_id': str(self.charity.pk), 'amount_minor': 99},
            content_type='application/json',
        )
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': ''}):
            unconfigured = self.client.post(
                '/api/payments/donations/checkout/',
                {'charity_id': str(self.charity.pk), 'amount_minor': 500},
                content_type='application/json',
            )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(unconfigured.status_code, 503)
        self.assertFalse(Donation.objects.exists())
        create_session.assert_not_called()

    @patch('apps.payments.views.stripe.checkout.Session.create')
    def test_demo_donation_checkout_rejects_live_stripe_keys(self, create_session):
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_live_not_for_demo'}):
            response = self.client.post(
                '/api/payments/donations/checkout/',
                {'charity_id': str(self.charity.pk), 'amount_minor': 500},
                content_type='application/json',
            )
            config = self.client.get('/api/payments/donations/config/')

        self.assertEqual(response.status_code, 503)
        self.assertFalse(config.json()['checkout_available'])
        self.assertFalse(Donation.objects.exists())
        create_session.assert_not_called()

    @patch('apps.payments.views.stripe.Webhook.construct_event')
    def test_signed_checkout_webhook_records_successful_donation_idempotently(self, construct_event):
        donation = Donation.objects.create(
            user=self.user,
            charity=self.charity,
            stripe_checkout_session_id='cs_webhook_donation',
            amount_minor=2500,
            currency='USD',
        )
        event = {
            'id': 'evt_donation_paid_test',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_webhook_donation',
                    'metadata': {'donation_id': str(donation.pk)},
                    'payment_status': 'paid',
                    'amount_total': 2500,
                    'currency': 'usd',
                    'payment_intent': 'pi_donation_test',
                },
            },
        }
        construct_event.return_value = event
        with patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
            first = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )
            second = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )

        donation.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertTrue(second.json()['duplicate'])
        self.assertEqual(donation.status, Donation.Status.SUCCEEDED)
        self.assertEqual(donation.stripe_payment_intent_id, 'pi_donation_test')
        self.assertIsNotNone(donation.paid_at)

    @patch('apps.payments.views.stripe.Webhook.construct_event')
    def test_subscription_checkout_completion_is_not_processed_as_donation(self, construct_event):
        event = {
            'id': 'evt_subscription_checkout_complete_test',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_subscription_test',
                    'mode': 'subscription',
                    'subscription': 'sub_webhook_test',
                },
            },
        }
        construct_event.return_value = event
        with patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
            response = self.client.post(
                '/api/payments/stripe/webhook/',
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test-signature',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeWebhookEvent.objects.get(stripe_event_id=event['id']).status, 'succeeded')
        self.assertFalse(Donation.objects.exists())
