from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.utils import timezone

from apps.draws.models import Draw, DrawConfiguration, DrawEntry, DrawResultNumber, DrawRun
from apps.draws.services import simulate_draw
from apps.payments.models import SubscriptionInvoice
from apps.scores.models import GolfScore
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.winners.models import DrawWinner


class DrawSimulationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='draw-member')
        self.plan = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.MONTHLY,
            amount_minor=1200,
            currency='USD',
        )
        self.now = timezone.now().replace(microsecond=0)
        self.subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=self.now - timedelta(days=20),
            current_period_end=self.now + timedelta(days=10),
        )
        SubscriptionInvoice.objects.create(
            subscription=self.subscription,
            stripe_invoice_id='in_draw_test',
            amount_minor=1200,
            currency='USD',
            status=SubscriptionInvoice.Status.PAID,
            period_start=self.subscription.current_period_start,
            period_end=self.subscription.current_period_end,
            paid_at=self.now - timedelta(days=19),
        )
        for offset, score in enumerate((31, 33, 35, 37, 39), start=5):
            GolfScore.objects.create(
                user=self.user,
                score_date=self.now.date() - timedelta(days=offset),
                score=score,
            )
        self.configuration = DrawConfiguration.objects.create(version=1, mode=DrawConfiguration.Mode.RANDOM)
        self.draw = Draw.objects.create(
            configuration=self.configuration,
            scheduled_at=self.now + timedelta(days=1),
            eligibility_cutoff=self.now,
        )
        self.client = Client()

    def test_simulation_snapshots_paid_eligible_members_and_never_publishes(self):
        run = simulate_draw(self.draw.pk, seed='stable-simulation-seed')

        self.draw.refresh_from_db()
        entry = DrawEntry.objects.get(draw=self.draw, user=self.user)
        values = list(entry.numbers.order_by('ordinal').values_list('number', flat=True))
        winning_numbers = list(run.winning_numbers.order_by('ordinal').values_list('number', flat=True))

        self.assertEqual(self.draw.status, Draw.Status.SIMULATED)
        self.assertEqual(run.run_type, DrawRun.RunType.SIMULATION)
        self.assertFalse(run.is_published)
        self.assertEqual(entry.score_snapshot[0]['score'], 31)
        self.assertEqual(values, [31, 33, 35, 37, 39])
        self.assertEqual(len(winning_numbers), 5)
        self.assertEqual(len(set(winning_numbers)), 5)
        self.assertTrue(all(1 <= number <= 45 for number in winning_numbers))
        self.assertFalse(DrawWinner.objects.exists())

    def test_subscriber_with_fewer_than_five_scores_is_not_entered(self):
        GolfScore.objects.filter(user=self.user).order_by('-score_date').first().delete()

        with self.assertRaises(ValidationError):
            simulate_draw(self.draw.pk, seed='not-enough-scores')

        self.assertEqual(DrawEntry.objects.filter(draw=self.draw).count(), 0)
        self.assertFalse(DrawRun.objects.filter(draw=self.draw).exists())

    def test_algorithmic_simulation_uses_versioned_weighted_strategy(self):
        self.configuration.mode = DrawConfiguration.Mode.ALGORITHMIC
        self.configuration.save(update_fields=('mode', 'updated_at'))

        run = simulate_draw(self.draw.pk, seed='weighted-simulation-seed')

        self.assertEqual(run.algorithm_version, 'algorithmic-v1')
        self.assertEqual(run.audit_metadata['score_match_policy'], 'unique')
        self.assertEqual(len(run.result_snapshot['winning_numbers']), 5)
        self.assertEqual(run.input_hash, run.input_hash.lower())

    def test_public_draw_list_only_returns_published_draws(self):
        response = self.client.get('/api/draws/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        self.draw.status = Draw.Status.PUBLISHED
        self.draw.save(update_fields=('status', 'updated_at'))
        published = self.client.get('/api/draws/')
        self.assertEqual([item['id'] for item in published.json()], [str(self.draw.pk)])

    def test_non_admin_cannot_run_a_simulation(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/api/draws/admin/{self.draw.pk}/simulate/')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_run_simulation_without_creating_winners(self):
        admin = get_user_model().objects.create_user(username='draw-admin', is_staff=True)
        self.client.force_login(admin)
        response = self.client.post(f'/api/draws/admin/{self.draw.pk}/simulate/')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['run']['run_type'], DrawRun.RunType.SIMULATION)
        self.assertFalse(DrawWinner.objects.exists())

    def test_admin_configuration_creates_the_prd_tier_records(self):
        admin = get_user_model().objects.create_user(username='draw-config-admin', is_staff=True)
        self.client.force_login(admin)
        response = self.client.post(
            '/api/draws/admin/configurations/',
            {
                'version': 2,
                'mode': DrawConfiguration.Mode.RANDOM,
                'candidate_min': 1,
                'candidate_max': 45,
                'number_count': 5,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        shares = [tier['share_bps'] for tier in response.json()['prize_tiers']]
        self.assertEqual(sum(shares), 10000)
        self.assertEqual(len(shares), 3)
