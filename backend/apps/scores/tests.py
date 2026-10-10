from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.scores.models import GolfScore
from apps.scores.services import save_golf_score
from apps.subscriptions.models import Subscription, SubscriptionPlan


class GolfScoreConstraintTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='score-member', password='test-password')

    def test_score_must_be_between_one_and_forty_five(self):
        score_date = date(2026, 10, 1)
        for value in (0, 46):
            with self.subTest(score=value):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        GolfScore.objects.create(
                            user=self.user,
                            score_date=score_date,
                            score=value,
                        )

    def test_user_cannot_have_two_scores_on_the_same_date(self):
        score_date = date(2026, 10, 1)
        GolfScore.objects.create(user=self.user, score_date=score_date, score=35)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GolfScore.objects.create(user=self.user, score_date=score_date, score=40)

    def test_saving_a_sixth_newest_score_retains_only_the_five_most_recent(self):
        for day in range(1, 7):
            save_golf_score(self.user, date(2026, 10, day), day + 30)

        retained = list(GolfScore.objects.filter(user=self.user).order_by('score_date'))
        self.assertEqual([item.score_date.day for item in retained], [2, 3, 4, 5, 6])

    def test_saving_an_existing_date_updates_instead_of_adding(self):
        score_date = date(2026, 10, 2)
        save_golf_score(self.user, score_date, 35)
        updated = save_golf_score(self.user, score_date, 41)

        self.assertEqual(GolfScore.objects.filter(user=self.user).count(), 1)
        self.assertEqual(updated.score, 41)

    def test_backdated_score_outside_the_latest_five_is_rejected_atomically(self):
        for day in range(2, 7):
            save_golf_score(self.user, date(2026, 10, day), day + 30)

        with self.assertRaises(ValidationError):
            save_golf_score(self.user, date(2026, 10, 1), 31)

        self.assertEqual(GolfScore.objects.filter(user=self.user).count(), 5)
        self.assertFalse(GolfScore.objects.filter(user=self.user, score_date=date(2026, 10, 1)).exists())

    def test_service_rejects_scores_outside_the_valid_range(self):
        with self.assertRaises(ValidationError):
            save_golf_score(self.user, date(2026, 10, 1), 46)


class ScoreApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='score-api-member',
            email='score-api@example.com',
            password='TallPine!River58',
        )
        UserProfile.objects.create(user=self.user, email='score-api@example.com')
        plan = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.MONTHLY,
            amount_minor=1000,
            currency='USD',
        )
        now = timezone.now()
        Subscription.objects.create(
            user=self.user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_active_subscriber_can_create_list_edit_and_delete_scores(self):
        first = self.client.post(
            '/api/scores/',
            {'score_date': '2026-10-01', 'score': 34},
            content_type='application/json',
        )
        self.assertEqual(first.status_code, 201)
        score_id = first.json()['id']

        updated = self.client.patch(
            f'/api/scores/{score_id}/',
            {'score': 42},
            content_type='application/json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['score'], 42)
        self.assertEqual(self.client.get('/api/scores/').json()[0]['score'], 42)

        deleted = self.client.delete(f'/api/scores/{score_id}/')
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(GolfScore.objects.filter(user=self.user).exists())

    def test_api_rejects_duplicate_score_date_instead_of_reporting_added(self):
        score_date = date(2026, 10, 1)
        save_golf_score(self.user, score_date, 34)

        response = self.client.post(
            '/api/scores/',
            {'score_date': score_date.isoformat(), 'score': 42},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['score_date'],
            ['A score has already been entered for this date.'],
        )
        self.assertEqual(
            list(GolfScore.objects.filter(user=self.user).values_list('score', flat=True)),
            [34],
        )

    def test_score_api_requires_an_active_subscription(self):
        Subscription.objects.update(status=Subscription.Status.CANCELED)
        response = self.client.get('/api/scores/')
        submission = self.client.post(
            '/api/scores/',
            {'score_date': '2026-10-01', 'score': 34},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'subscription_required')
        self.assertEqual(
            response.json()['detail'],
            'To enter a golf score, please purchase a subscription plan.',
        )
        self.assertEqual(submission.status_code, 403)
        self.assertEqual(submission.json()['code'], 'subscription_required')
        self.assertFalse(GolfScore.objects.filter(user=self.user).exists())

    def test_api_creation_applies_the_rolling_five_rule(self):
        for day in range(1, 7):
            response = self.client.post(
                '/api/scores/',
                {'score_date': f'2026-10-{day:02d}', 'score': day + 30},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 201)

        self.assertEqual(GolfScore.objects.filter(user=self.user).count(), 5)
        self.assertFalse(GolfScore.objects.filter(user=self.user, score_date=date(2026, 10, 1)).exists())
