import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.payments.models import StripeCustomer, StripeWebhookEvent
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
