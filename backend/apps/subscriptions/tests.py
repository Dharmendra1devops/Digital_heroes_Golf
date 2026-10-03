import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.payments.models import StripeCustomer
from apps.subscriptions.models import Subscription, SubscriptionPlan


class SubscriptionApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='subscription-member',
            email='subscription@example.com',
            password='TallPine!River58',
        )
        self.client.force_login(self.user)
        self.plan = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.MONTHLY,
            amount_minor=1200,
            currency='USD',
            stripe_price_id='price_monthly_test',
        )

    def test_checkout_fails_closed_without_a_stripe_secret(self):
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': ''}):
            response = self.client.post(
                '/api/subscriptions/checkout/',
                {'interval': 'monthly'},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'stripe_not_configured')

    @patch('apps.subscriptions.views.stripe.checkout.Session.create')
    @patch('apps.subscriptions.views.stripe.Customer.create')
    def test_checkout_creates_customer_once_and_returns_hosted_url(self, create_customer, create_session):
        create_customer.return_value.id = 'cus_test_123'
        create_session.return_value.url = 'https://checkout.stripe.test/session'
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_test_fake'}):
            response = self.client.post(
                '/api/subscriptions/checkout/',
                {'interval': 'monthly'},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.stripe.test/session')
        self.assertEqual(StripeCustomer.objects.get(user=self.user).stripe_customer_id, 'cus_test_123')
        create_customer.assert_called_once()
        create_session.assert_called_once()

    def test_public_plans_do_not_expose_stripe_price_ids(self):
        response = self.client.get('/api/subscriptions/plans/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['interval'], 'monthly')
        self.assertNotIn('stripe_price_id', response.json()[0])

    def test_only_staff_can_configure_subscription_plans(self):
        denied = self.client.post(
            '/api/subscriptions/admin/plans/',
            {
                'interval': 'yearly',
                'amount_minor': 12000,
                'currency': 'USD',
                'stripe_price_id': 'price_yearly_denied',
                'is_active': True,
            },
            content_type='application/json',
        )
        self.assertEqual(denied.status_code, 403)

        admin = get_user_model().objects.create_user(username='plan-admin', is_staff=True)
        self.client.force_login(admin)
        allowed = self.client.post(
            '/api/subscriptions/admin/plans/',
            {
                'interval': 'yearly',
                'amount_minor': 12000,
                'currency': 'USD',
                'stripe_price_id': 'price_yearly_test',
                'is_active': True,
            },
            content_type='application/json',
        )
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(allowed.json()['interval'], 'yearly')

    def test_cancel_marks_renewal_off_only_after_stripe_confirms(self):
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_cancel_test',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_test_fake'}):
            with patch('apps.subscriptions.views.stripe.Subscription.modify') as modify:
                modify.return_value = SimpleNamespace(cancel_at_period_end=True)
                response = self.client.post('/api/subscriptions/me/cancel/')

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertTrue(subscription.cancel_at_period_end)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        modify.assert_called_once_with('sub_cancel_test', cancel_at_period_end=True, api_key='sk_test_fake')

    def test_cancel_fails_closed_without_stripe_configuration(self):
        now = timezone.now()
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_cancel_unconfigured',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': ''}):
            response = self.client.post('/api/subscriptions/me/cancel/')

        self.assertEqual(response.status_code, 503)
