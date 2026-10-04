from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import UserProfile
from apps.charities.models import Charity, CharitySelection
from apps.draws.models import DrawConfiguration, Draw, DrawTierPool
from apps.payments.models import Donation, FundingAllocation, SubscriptionInvoice
from apps.scores.models import GolfScore
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.winners.models import DrawWinner


class AccountApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def csrf_headers(self):
        self.client.get('/api/auth/csrf/')
        return {'HTTP_X_CSRFTOKEN': self.client.cookies['csrftoken'].value}

    def test_registration_requires_csrf_and_starts_a_session(self):
        payload = {
            'email': 'member@example.com',
            'display_name': 'Avery Member',
            'password': 'TallPine!River58',
        }
        denied = self.client.post('/api/auth/register/', payload, content_type='application/json')
        self.assertEqual(denied.status_code, 403)

        response = self.client.post(
            '/api/auth/register/',
            payload,
            content_type='application/json',
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserProfile.objects.get().email, 'member@example.com')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)

    def test_login_uses_email_and_rejects_invalid_credentials(self):
        user = get_user_model().objects.create_user(
            username='account-login-test',
            email='login@example.com',
            password='TallPine!River58',
        )
        UserProfile.objects.create(user=user, email='login@example.com')
        headers = self.csrf_headers()

        invalid = self.client.post(
            '/api/auth/login/',
            {'email': 'login@example.com', 'password': 'wrong-password'},
            content_type='application/json',
            **headers,
        )
        self.assertEqual(invalid.status_code, 400)

        valid = self.client.post(
            '/api/auth/login/',
            {'email': 'LOGIN@example.com', 'password': 'TallPine!River58'},
            content_type='application/json',
            **headers,
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()['user']['email'], 'login@example.com')

    def test_member_can_update_display_name_without_changing_email(self):
        user = get_user_model().objects.create_user(
            username='profile-settings-test',
            email='profile@example.com',
            password='TallPine!River58',
        )
        UserProfile.objects.create(user=user, email='profile@example.com', display_name='Old Name')
        self.client.force_login(user)

        response = self.client.patch(
            '/api/auth/me/',
            {'display_name': 'New Name'},
            content_type='application/json',
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['display_name'], 'New Name')
        self.assertEqual(response.json()['user']['email'], 'profile@example.com')

    def test_member_can_change_password_and_keep_their_session(self):
        user = get_user_model().objects.create_user(
            username='password-settings-test',
            email='password@example.com',
            password='TallPine!River58',
        )
        self.client.force_login(user)

        response = self.client.post(
            '/api/auth/me/password/',
            {
                'current_password': 'TallPine!River58',
                'new_password': 'BrightLake!Forest94',
            },
            content_type='application/json',
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password('BrightLake!Forest94'))

    def test_password_change_rejects_wrong_current_password(self):
        user = get_user_model().objects.create_user(
            username='password-settings-invalid',
            email='password-invalid@example.com',
            password='TallPine!River58',
        )
        self.client.force_login(user)

        response = self.client.post(
            '/api/auth/me/password/',
            {
                'current_password': 'wrong-current-password',
                'new_password': 'BrightLake!Forest94',
            },
            content_type='application/json',
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password('TallPine!River58'))

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        user = get_user_model().objects.create_user(username='existing-account')
        UserProfile.objects.create(user=user, email='duplicate@example.com')
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'DUPLICATE@example.com',
                'password': 'TallPine!River58',
            },
            content_type='application/json',
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_registration_requires_and_saves_a_charity_when_directory_is_populated(self):
        charity = Charity.objects.create(
            slug='demo-community-cause',
            name='Demo Community Cause',
        )
        headers = self.csrf_headers()
        missing_charity = self.client.post(
            '/api/auth/register/',
            {
                'email': 'member-without-cause@example.com',
                'password': 'TallPine!River58',
            },
            content_type='application/json',
            **headers,
        )
        self.assertEqual(missing_charity.status_code, 400)

        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'member-with-cause@example.com',
                'display_name': 'Cause Member',
                'password': 'TallPine!River58',
                'charity_id': str(charity.pk),
                'contribution_bps': 1500,
            },
            content_type='application/json',
            **headers,
        )

        self.assertEqual(response.status_code, 201)
        selection = CharitySelection.objects.get(user__profile__email='member-with-cause@example.com')
        self.assertEqual(selection.charity, charity)
        self.assertEqual(selection.contribution_bps, 1500)

    def test_registration_rejects_invalid_charity_contribution(self):
        charity = Charity.objects.create(slug='demo-cause', name='Demo Cause')
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'invalid-contribution@example.com',
                'password': 'TallPine!River58',
                'charity_id': str(charity.pk),
                'contribution_bps': 999,
            },
            content_type='application/json',
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            get_user_model().objects.filter(profile__email='invalid-contribution@example.com').exists(),
        )

    def test_admin_can_view_edit_and_deactivate_member_without_editing_staff(self):
        admin = get_user_model().objects.create_user(username='member-manager', is_staff=True)
        member = get_user_model().objects.create_user(
            username='member-managed',
            email='old@example.com',
            date_joined=timezone.now(),
        )
        UserProfile.objects.create(user=member, email='old@example.com', display_name='Old Name')
        score = GolfScore.objects.create(user=member, score_date=timezone.now().date(), score=28)
        self.client.force_login(admin)

        listing = self.client.get('/api/auth/admin/users/?q=old')
        updated = self.client.patch(
            f'/api/auth/admin/users/{member.pk}/',
            {'email': 'new@example.com', 'display_name': 'New Name', 'is_active': False},
            content_type='application/json',
            **self.csrf_headers(),
        )
        score_update = self.client.patch(
            f'/api/auth/admin/users/{member.pk}/scores/{score.pk}/',
            {'score': 35},
            content_type='application/json',
            **self.csrf_headers(),
        )
        staff_edit = self.client.patch(
            f'/api/auth/admin/users/{admin.pk}/',
            {'display_name': 'Not allowed'},
            content_type='application/json',
            **self.csrf_headers(),
        )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()['results'][0]['email'], 'old@example.com')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['display_name'], 'New Name')
        self.assertFalse(updated.json()['is_active'])
        self.assertEqual(score_update.status_code, 200)
        self.assertEqual(score_update.json()['score'], 35)
        self.assertEqual(staff_edit.status_code, 404)

    def test_admin_score_updates_validate_range_and_preserve_five_score_limit(self):
        admin = get_user_model().objects.create_user(username='score-manager', is_staff=True)
        member = get_user_model().objects.create_user(username='score-managed')
        scores = [
            GolfScore.objects.create(
                user=member,
                score_date=timezone.now().date() - timedelta(days=day),
                score=30 + day,
            )
            for day in range(5)
        ]
        self.client.force_login(admin)

        invalid = self.client.patch(
            f'/api/auth/admin/users/{member.pk}/scores/{scores[0].pk}/',
            {'score': 46},
            content_type='application/json',
            **self.csrf_headers(),
        )
        valid = self.client.patch(
            f'/api/auth/admin/users/{member.pk}/scores/{scores[0].pk}/',
            {'score': 42},
            content_type='application/json',
            **self.csrf_headers(),
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(GolfScore.objects.filter(user=member).count(), 5)
        self.assertEqual(GolfScore.objects.get(pk=scores[0].pk).score, 42)

    def test_admin_user_management_and_reports_require_staff(self):
        member = get_user_model().objects.create_user(username='member-no-admin')
        self.client.force_login(member)

        listing = self.client.get('/api/auth/admin/users/')
        overview = self.client.get('/api/auth/admin/overview/')

        self.assertEqual(listing.status_code, 403)
        self.assertEqual(overview.status_code, 403)

    def test_admin_overview_reports_users_draws_pools_and_charity_donations(self):
        admin = get_user_model().objects.create_user(username='reporting-admin', is_staff=True)
        member = get_user_model().objects.create_user(username='reporting-member')
        plan = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.MONTHLY,
            amount_minor=1200,
            currency='USD',
        )
        subscription = Subscription.objects.create(
            user=member,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        invoice = SubscriptionInvoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='in_admin_report',
            amount_minor=1200,
            currency='USD',
            status=SubscriptionInvoice.Status.PAID,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            paid_at=timezone.now(),
        )
        draw_config = DrawConfiguration.objects.create(version=1, mode=DrawConfiguration.Mode.RANDOM)
        draw = Draw.objects.create(
            configuration=draw_config,
            scheduled_at=timezone.now() + timedelta(days=2),
            eligibility_cutoff=timezone.now(),
        )
        FundingAllocation.objects.create(
            invoice=invoice,
            draw=draw,
            allocation_type=FundingAllocation.Type.PRIZE_POOL,
            amount_minor=300,
            currency='USD',
            idempotency_key='271c9143-507a-4fe0-a70e-723c3b52021a',
        )
        DrawTierPool.objects.create(
            draw=draw,
            match_count=5,
            share_bps=4000,
            available_minor=300,
            currency='USD',
        )
        charity = Charity.objects.create(slug='report-charity', name='Report Charity')
        Donation.objects.create(
            user=member,
            charity=charity,
            amount_minor=500,
            currency='USD',
            status=Donation.Status.SUCCEEDED,
            paid_at=timezone.now(),
        )
        self.client.force_login(admin)

        response = self.client.get('/api/auth/admin/overview/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_users'], 1)
        self.assertEqual(response.json()['active_subscribers'], 1)
        self.assertEqual(response.json()['prize_funding_by_currency'][0]['amount_minor'], 300)
        self.assertEqual(response.json()['charity_contributions_by_currency'][0]['amount_minor'], 500)
        self.assertEqual(response.json()['distributed_pools_by_currency'][0]['distributed_minor'], 300)
        Donation.objects.create(
            user=member,
            charity=charity,
            amount_minor=250,
            currency='EUR',
            status=Donation.Status.SUCCEEDED,
            paid_at=timezone.now(),
        )
        currencies = self.client.get('/api/auth/admin/overview/').json()[
            'charity_contributions_by_currency'
        ]
        self.assertEqual(
            currencies,
            [
                {'currency': 'EUR', 'amount_minor': 250},
                {'currency': 'USD', 'amount_minor': 500},
            ],
        )
