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

    @patch('apps.subscriptions.views.stripe.Subscription.modify')
    def test_admin_can_cancel_and_resume_member_subscription_through_stripe(self, modify):
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_admin_action_test',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        admin = get_user_model().objects.create_user(username='subscription-admin-action', is_staff=True)
        self.client.force_login(admin)
        modify.side_effect = [
            SimpleNamespace(cancel_at_period_end=True),
            SimpleNamespace(cancel_at_period_end=False),
        ]
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_test_fake'}):
            cancelled = self.client.post(
                f'/api/subscriptions/admin/subscriptions/{subscription.pk}/action/',
                {'action': 'cancel'},
                content_type='application/json',
            )
            resumed = self.client.post(
                f'/api/subscriptions/admin/subscriptions/{subscription.pk}/action/',
                {'action': 'resume'},
                content_type='application/json',
            )

        self.assertEqual(cancelled.status_code, 200)
        self.assertTrue(cancelled.json()['subscription']['cancel_at_period_end'])
        self.assertEqual(resumed.status_code, 200)
        self.assertFalse(resumed.json()['subscription']['cancel_at_period_end'])
        modify.assert_any_call(
            'sub_admin_action_test',
            cancel_at_period_end=True,
            api_key='sk_test_fake',
        )
        modify.assert_any_call(
            'sub_admin_action_test',
            cancel_at_period_end=False,
            api_key='sk_test_fake',
        )
        subscription.refresh_from_db()
        self.assertFalse(subscription.cancel_at_period_end)
        self.assertIsNone(subscription.canceled_at)

    @patch('apps.subscriptions.views.stripe.Subscription.modify')
    def test_admin_subscription_action_requires_staff_and_test_key(self, modify):
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_admin_action_protection',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        denied = self.client.post(
            f'/api/subscriptions/admin/subscriptions/{subscription.pk}/action/',
            {'action': 'cancel'},
            content_type='application/json',
        )
        self.assertEqual(denied.status_code, 403)

        admin = get_user_model().objects.create_user(username='subscription-live-key-admin', is_staff=True)
        self.client.force_login(admin)
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_live_not_for_demo'}):
            rejected = self.client.post(
                f'/api/subscriptions/admin/subscriptions/{subscription.pk}/action/',
                {'action': 'cancel'},
                content_type='application/json',
            )

        self.assertEqual(rejected.status_code, 503)
        self.assertEqual(rejected.json()['code'], 'stripe_not_configured')
        modify.assert_not_called()

    @patch('apps.subscriptions.views.stripe.checkout.Session.create')
    @patch('apps.subscriptions.views.stripe.Customer.create')
    def test_demo_checkout_rejects_live_stripe_keys(self, create_customer, create_session):
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_live_not_for_demo'}):
            response = self.client.post(
                '/api/subscriptions/checkout/',
                {'interval': 'monthly'},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'stripe_not_configured')
        create_customer.assert_not_called()
        create_session.assert_not_called()

    @patch('apps.subscriptions.views.stripe.checkout.Session.create')
    @patch('apps.subscriptions.views.stripe.Customer.create')
    def test_checkout_creates_customer_once_and_returns_hosted_url(self, create_customer, create_session):
        create_customer.return_value.id = 'cus_test_123'
        create_session.return_value.url = 'https://checkout.stripe.test/session'
        with patch.dict(os.environ, {
            'STRIPE_SECRET_KEY': 'sk_test_fake',
            'FRONTEND_BASE_URL': 'http://localhost:3000',
        }):
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
        self.assertEqual(
            create_session.call_args.kwargs['success_url'],
            'http://localhost:3000/dashboard?checkout=success',
        )
        self.assertEqual(
            create_session.call_args.kwargs['cancel_url'],
            'http://localhost:3000/subscribe?checkout=cancelled',
        )

    def test_public_plans_do_not_expose_stripe_price_ids(self):
        response = self.client.get('/api/subscriptions/plans/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['interval'], 'monthly')
        self.assertNotIn('stripe_price_id', response.json()[0])

    def test_public_plans_are_not_checkout_ready_with_live_key_in_demo(self):
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_live_not_for_demo'}):
            response = self.client.get('/api/subscriptions/plans/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()[0]['checkout_available'])

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

    def test_staff_can_edit_plan_amount_currency_and_stripe_price_mapping(self):
        admin = get_user_model().objects.create_user(username='plan-editor', is_staff=True)
        self.client.force_login(admin)

        response = self.client.patch(
            f'/api/subscriptions/admin/plans/{self.plan.pk}/',
            {
                'amount_minor': 29900,
                'currency': 'inr',
                'stripe_price_id': 'price_monthly_inr_v2',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.amount_minor, 29900)
        self.assertEqual(self.plan.currency, 'INR')
        self.assertEqual(self.plan.stripe_price_id, 'price_monthly_inr_v2')

    def test_staff_plan_edits_reject_invalid_price_ids_and_currency(self):
        admin = get_user_model().objects.create_user(username='plan-validator', is_staff=True)
        self.client.force_login(admin)

        invalid_price = self.client.patch(
            f'/api/subscriptions/admin/plans/{self.plan.pk}/',
            {'stripe_price_id': 'not-a-stripe-price'},
            content_type='application/json',
        )
        invalid_currency = self.client.patch(
            f'/api/subscriptions/admin/plans/{self.plan.pk}/',
            {'currency': '₹'},
            content_type='application/json',
        )

        self.assertEqual(invalid_price.status_code, 400)
        self.assertEqual(invalid_currency.status_code, 400)

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

    @patch('apps.subscriptions.views.stripe.Subscription.modify')
    @patch('apps.subscriptions.views.stripe.Subscription.retrieve')
    def test_member_plan_change_prorates_the_current_subscription(self, retrieve, modify):
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_member_change_test',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        target = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.YEARLY,
            amount_minor=12000,
            currency='USD',
            stripe_price_id='price_yearly_test',
        )
        retrieve.return_value = SimpleNamespace(
            items=SimpleNamespace(data=[SimpleNamespace(id='si_member_change_test')]),
        )
        modify.return_value = SimpleNamespace(
            status=Subscription.Status.ACTIVE,
            items=SimpleNamespace(
                data=[SimpleNamespace(price=SimpleNamespace(id='price_yearly_test'))],
            ),
        )

        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_test_fake'}):
            response = self.client.post(
                '/api/subscriptions/me/change-plan/',
                {'plan_id': str(target.pk)},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['subscription']['plan']['interval'], 'yearly')
        retrieve.assert_called_once_with('sub_member_change_test', api_key='sk_test_fake')
        modify.assert_called_once_with(
            'sub_member_change_test',
            items=[{'id': 'si_member_change_test', 'price': 'price_yearly_test'}],
            proration_behavior='create_prorations',
            payment_behavior='error_if_incomplete',
            api_key='sk_test_fake',
        )
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan_id, target.pk)

    def test_member_plan_change_rejects_live_keys_without_calling_stripe(self):
        now = timezone.now()
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_member_change_live_key',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        target = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.YEARLY,
            amount_minor=12000,
            currency='USD',
            stripe_price_id='price_yearly_test',
        )
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_live_not_for_demo'}):
            response = self.client.post(
                '/api/subscriptions/me/change-plan/',
                {'plan_id': str(target.pk)},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'stripe_not_configured')

    @patch('apps.subscriptions.views.stripe.Subscription.modify')
    @patch('apps.subscriptions.views.stripe.Subscription.retrieve')
    def test_member_plan_change_keeps_local_plan_when_stripe_does_not_confirm_price(self, retrieve, modify):
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_member_change_unconfirmed',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        target = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.YEARLY,
            amount_minor=12000,
            currency='USD',
            stripe_price_id='price_yearly_unconfirmed_test',
        )
        retrieve.return_value = SimpleNamespace(
            items=SimpleNamespace(data=[SimpleNamespace(id='si_member_change_unconfirmed')]),
        )
        modify.return_value = SimpleNamespace(
            status=Subscription.Status.ACTIVE,
            items=SimpleNamespace(
                data=[SimpleNamespace(price=SimpleNamespace(id='price_monthly_test'))],
            ),
        )

        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_test_fake'}):
            response = self.client.post(
                '/api/subscriptions/me/change-plan/',
                {'plan_id': str(target.pk)},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 502)
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan_id, self.plan.pk)

    @patch('apps.subscriptions.views.stripe.Subscription.modify')
    def test_member_can_resume_a_cancellation_after_stripe_confirms(self, modify):
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            stripe_subscription_id='sub_member_resume_test',
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=True,
            canceled_at=now,
        )
        modify.return_value = SimpleNamespace(cancel_at_period_end=False)
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_test_fake'}):
            response = self.client.post('/api/subscriptions/me/resume/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['subscription']['cancel_at_period_end'])
        modify.assert_called_once_with(
            'sub_member_resume_test',
            cancel_at_period_end=False,
            api_key='sk_test_fake',
        )
        subscription.refresh_from_db()
        self.assertIsNone(subscription.canceled_at)
