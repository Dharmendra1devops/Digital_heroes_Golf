from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from apps.charities.models import Charity, CharitySelection
from apps.draws.models import (
    Draw,
    DrawConfiguration,
    DrawEntry,
    DrawPrizeTierConfiguration,
    DrawRun,
    DrawTierPool,
)
from apps.draws.services import publish_draw, simulate_draw
from apps.payments.models import FundingAllocation, SubscriptionInvoice
from apps.scores.models import GolfScore
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.winners.models import DrawWinner, Payout


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
        self.configuration = DrawConfiguration.objects.create(
            version=1,
            mode=DrawConfiguration.Mode.RANDOM,
            prize_pool_contribution_bps=2500,
        )
        DrawPrizeTierConfiguration.objects.bulk_create([
            DrawPrizeTierConfiguration(
                configuration=self.configuration,
                match_count=5,
                share_bps=4000,
                rollover_unclaimed=True,
            ),
            DrawPrizeTierConfiguration(
                configuration=self.configuration,
                match_count=4,
                share_bps=3500,
                rollover_unclaimed=False,
            ),
            DrawPrizeTierConfiguration(
                configuration=self.configuration,
                match_count=3,
                share_bps=2500,
                rollover_unclaimed=False,
            ),
        ])
        self.draw = Draw.objects.create(
            configuration=self.configuration,
            scheduled_at=self.now + timedelta(days=1),
            eligibility_cutoff=self.now - timedelta(hours=1),
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

    def test_paid_invoice_after_cutoff_does_not_qualify_member(self):
        invoice = SubscriptionInvoice.objects.get(stripe_invoice_id='in_draw_test')
        invoice.paid_at = self.draw.eligibility_cutoff + timedelta(seconds=1)
        invoice.save(update_fields=('paid_at', 'updated_at'))

        with self.assertRaises(ValidationError):
            simulate_draw(self.draw.pk, seed='invoice-paid-after-cutoff')

        self.assertFalse(DrawEntry.objects.filter(draw=self.draw, user=self.user).exists())
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

        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=('candidate_min', 'candidate_max', 'number_count', 'updated_at'))
        simulate_draw(self.draw.pk, seed='public-result-seed')
        publish_draw(self.draw.pk, self.user)
        published = self.client.get('/api/draws/')
        results = published.json()
        self.assertEqual([item['id'] for item in results], [str(self.draw.pk)])
        self.assertEqual(len(results[0]['winning_numbers']), 5)
        self.assertEqual(len(results[0]['prize_pools']), 3)

    def test_member_draw_summary_shows_only_the_signed_in_members_activity(self):
        other_user = get_user_model().objects.create_user(username='private-draw-member')
        self.client.force_login(self.user)

        anonymous_response = Client().get('/api/draws/me/summary/')
        response = self.client.get('/api/draws/me/summary/')
        self.client.force_login(other_user)
        other_response = self.client.get('/api/draws/me/summary/')

        self.assertEqual(anonymous_response.status_code, 403)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['draws_entered'], 0)
        self.assertEqual(response.json()['upcoming_draws'][0]['entered'], False)
        self.assertEqual(other_response.json()['draws_entered'], 0)
        self.assertEqual(other_response.json()['winnings_by_currency'], [])

    def test_member_draw_summary_includes_entry_and_currency_separated_payout_state(self):
        run = simulate_draw(self.draw.pk, seed='member-summary-entry')
        entry = DrawEntry.objects.get(draw=self.draw, user=self.user)
        winner = DrawWinner.objects.create(
            entry=entry,
            match_count=3,
            prize_amount_minor=5000,
            currency='USD',
        )
        Payout.objects.create(
            winner=winner,
            attempt_number=1,
            amount_minor=5000,
            currency='USD',
        )
        self.client.force_login(self.user)

        response = self.client.get('/api/draws/me/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['draws_entered'], 1)
        self.assertTrue(response.json()['upcoming_draws'][0]['entered'])
        self.assertEqual(response.json()['winnings_by_currency'], [{'currency': 'USD', 'amount_minor': 5000}])
        self.assertEqual(response.json()['payouts_by_status'][0]['status'], 'pending')
        self.assertEqual(response.json()['payouts_by_status'][0]['count'], 1)

    def test_non_admin_cannot_run_a_simulation(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/api/draws/admin/{self.draw.pk}/simulate/')
        publish_response = self.client.post(f'/api/draws/admin/{self.draw.pk}/publish/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(publish_response.status_code, 403)

    def test_admin_can_run_simulation_without_creating_winners(self):
        admin = get_user_model().objects.create_user(username='draw-admin', is_staff=True)
        self.client.force_login(admin)
        response = self.client.post(f'/api/draws/admin/{self.draw.pk}/simulate/')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['run']['run_type'], DrawRun.RunType.SIMULATION)
        self.assertEqual(len(response.json()['run']['result_snapshot']['winning_numbers']), 5)

        refreshed_draw = next(
            item for item in self.client.get('/api/draws/admin/').json()
            if item['id'] == str(self.draw.pk)
        )
        self.assertEqual(
            refreshed_draw['simulation_run']['result_snapshot']['winning_numbers'],
            response.json()['run']['result_snapshot']['winning_numbers'],
        )
        self.assertFalse(DrawWinner.objects.exists())

    def test_admin_can_publish_a_simulated_draw(self):
        admin = get_user_model().objects.create_user(username='draw-publish-admin', is_staff=True)
        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=('candidate_min', 'candidate_max', 'number_count', 'updated_at'))
        self.client.force_login(admin)
        simulated = self.client.post(f'/api/draws/admin/{self.draw.pk}/simulate/')
        response = self.client.post(f'/api/draws/admin/{self.draw.pk}/publish/')

        self.assertEqual(simulated.status_code, 201)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['run']['run_type'], DrawRun.RunType.PUBLISH)
        self.draw.refresh_from_db()
        self.assertEqual(self.draw.status, Draw.Status.PUBLISHED)

    def test_publishing_settles_prizes_and_carries_an_unclaimed_jackpot(self):
        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=('candidate_min', 'candidate_max', 'number_count', 'updated_at'))
        simulate_draw(self.draw.pk, seed='publish-result-seed')

        run = publish_draw(self.draw.pk, self.user)

        self.draw.refresh_from_db()
        jackpot = DrawTierPool.objects.get(draw=self.draw, match_count=5)
        third_tier = DrawTierPool.objects.get(draw=self.draw, match_count=3)
        winner = DrawWinner.objects.get(entry__draw=self.draw, match_count=3)
        payout = Payout.objects.get(winner=winner)
        self.assertEqual(self.draw.status, Draw.Status.PUBLISHED)
        self.assertTrue(run.is_published)
        self.assertEqual(run.run_type, DrawRun.RunType.PUBLISH)
        self.assertEqual(FundingAllocation.objects.filter(draw=self.draw).count(), 1)
        self.assertEqual(FundingAllocation.objects.get(draw=self.draw).amount_minor, 300)
        self.assertEqual(jackpot.available_minor, 120)
        self.assertEqual(jackpot.rollover_out_minor, 120)
        self.assertEqual(third_tier.available_minor, 75)
        self.assertEqual(winner.prize_amount_minor, 75)
        self.assertEqual(payout.amount_minor, 75)
        self.assertEqual(payout.status, Payout.Status.PENDING)

        next_draw = Draw.objects.create(
            configuration=self.configuration,
            scheduled_at=self.draw.scheduled_at + timedelta(days=30),
            eligibility_cutoff=self.draw.eligibility_cutoff,
        )
        simulate_draw(next_draw.pk, seed='following-result-seed')
        publish_draw(next_draw.pk, self.user)
        next_jackpot = DrawTierPool.objects.get(draw=next_draw, match_count=5)
        self.assertEqual(next_jackpot.rollover_in_minor, 120)
        self.assertEqual(next_jackpot.available_minor, 240)

    def test_annual_subscription_contributes_one_twelfth_per_monthly_draw(self):
        yearly_plan = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.YEARLY,
            amount_minor=12000,
            currency='USD',
        )
        self.subscription.plan = yearly_plan
        self.subscription.save(update_fields=('plan', 'updated_at'))
        invoice = SubscriptionInvoice.objects.get(stripe_invoice_id='in_draw_test')
        invoice.amount_minor = 12000
        invoice.save(update_fields=('amount_minor', 'updated_at'))
        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=('candidate_min', 'candidate_max', 'number_count', 'updated_at'))
        simulate_draw(self.draw.pk, seed='annual-result-seed')

        publish_draw(self.draw.pk, self.user)

        allocation = FundingAllocation.objects.get(draw=self.draw)
        self.assertEqual(allocation.amount_minor, 250)

    def test_prize_and_selected_charity_contributions_cannot_overallocate_a_paid_invoice(self):
        charity = Charity.objects.create(slug='draw-contribution-cause', name='Draw Cause')
        CharitySelection.objects.create(
            user=self.user,
            charity=charity,
            contribution_bps=8000,
            effective_from=self.subscription.current_period_start - timedelta(days=1),
        )
        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=('candidate_min', 'candidate_max', 'number_count', 'updated_at'))
        simulate_draw(self.draw.pk, seed='overallocated-contribution-seed')

        with self.assertRaisesMessage(ValidationError, 'cannot exceed the subscription payment'):
            publish_draw(self.draw.pk, self.user)

        self.assertFalse(FundingAllocation.objects.filter(draw=self.draw).exists())
        self.assertFalse(DrawTierPool.objects.filter(draw=self.draw).exists())

    def test_multiple_winners_split_their_tier_pool_with_only_minor_unit_rounding(self):
        second_user = get_user_model().objects.create_user(username='second-draw-member')
        second_subscription = Subscription.objects.create(
            user=second_user,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=self.now - timedelta(days=20),
            current_period_end=self.now + timedelta(days=10),
        )
        invoice = SubscriptionInvoice.objects.create(
            subscription=second_subscription,
            stripe_invoice_id='in_second_draw_member',
            amount_minor=1208,
            currency='USD',
            status=SubscriptionInvoice.Status.PAID,
            period_start=second_subscription.current_period_start,
            period_end=second_subscription.current_period_end,
            paid_at=self.now - timedelta(days=19),
        )
        base_invoice = SubscriptionInvoice.objects.get(stripe_invoice_id='in_draw_test')
        base_invoice.amount_minor = 1208
        base_invoice.save(update_fields=('amount_minor', 'updated_at'))
        for offset, score in enumerate((31, 33, 35, 37, 39), start=5):
            GolfScore.objects.create(
                user=second_user,
                score_date=self.now.date() - timedelta(days=offset),
                score=score,
            )
        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=('candidate_min', 'candidate_max', 'number_count', 'updated_at'))
        simulate_draw(self.draw.pk, seed='multiple-winner-result')

        publish_draw(self.draw.pk, self.user)

        winners = list(
            DrawWinner.objects.filter(entry__draw=self.draw, match_count=3)
            .order_by('entry__user_id')
        )
        prizes = [winner.prize_amount_minor for winner in winners]
        self.assertEqual(len(winners), 2)
        self.assertEqual(sum(prizes), 151)
        self.assertEqual(max(prizes) - min(prizes), 1)
        self.assertEqual(invoice.amount_minor, 1208)
        self.assertEqual(Payout.objects.filter(winner__in=winners).count(), 2)

    def test_active_paid_subscribers_without_draw_entries_still_fund_the_pool(self):
        subscriber = get_user_model().objects.create_user(username='funding-only-member')
        subscription = Subscription.objects.create(
            user=subscriber,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=self.now - timedelta(days=1),
            current_period_end=self.now + timedelta(days=30),
        )
        SubscriptionInvoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='in_funding_only',
            amount_minor=1200,
            currency='USD',
            status=SubscriptionInvoice.Status.PAID,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            paid_at=self.now - timedelta(hours=1),
        )
        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=('candidate_min', 'candidate_max', 'number_count', 'updated_at'))
        simulate_draw(self.draw.pk, seed='active-subscriber-funding')

        publish_draw(self.draw.pk, self.user)

        self.assertEqual(DrawEntry.objects.filter(draw=self.draw).count(), 1)
        self.assertEqual(FundingAllocation.objects.filter(draw=self.draw).count(), 2)
        self.assertEqual(
            sum(FundingAllocation.objects.filter(draw=self.draw).values_list('amount_minor', flat=True)),
            600,
        )

    def test_publishing_requires_a_configured_contribution(self):
        self.configuration.prize_pool_contribution_bps = None
        self.configuration.candidate_min = 31
        self.configuration.candidate_max = 35
        self.configuration.number_count = 5
        self.configuration.save(update_fields=(
            'prize_pool_contribution_bps',
            'candidate_min',
            'candidate_max',
            'number_count',
            'updated_at',
        ))
        simulate_draw(self.draw.pk, seed='missing-contribution')

        with self.assertRaises(ValidationError):
            publish_draw(self.draw.pk, self.user)

        self.draw.refresh_from_db()
        self.assertEqual(self.draw.status, Draw.Status.SIMULATED)
        self.assertFalse(FundingAllocation.objects.filter(draw=self.draw).exists())
        self.assertFalse(DrawWinner.objects.filter(entry__draw=self.draw).exists())

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
                'prize_pool_contribution_bps': 2500,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        shares = [tier['share_bps'] for tier in response.json()['prize_tiers']]
        self.assertEqual(sum(shares), 10000)
        self.assertEqual(len(shares), 3)
        self.assertEqual(response.json()['prize_pool_contribution_bps'], 2500)


class ExampleDrawCommandTests(TestCase):
    def test_command_creates_unpublished_draw_and_is_idempotent(self):
        call_command('seed_example_draw')
        call_command('seed_example_draw')

        configuration = DrawConfiguration.objects.get(
            parameters__seed_key='portfolio-example-draw',
        )
        draw = Draw.objects.get(configuration=configuration)
        tiers = list(
            DrawPrizeTierConfiguration.objects.filter(configuration=configuration)
            .order_by('-match_count')
            .values_list('match_count', 'share_bps', 'rollover_unclaimed')
        )

        self.assertEqual(configuration.mode, DrawConfiguration.Mode.RANDOM)
        self.assertEqual(configuration.number_count, 5)
        self.assertIsNone(configuration.prize_pool_contribution_bps)
        self.assertEqual(draw.status, Draw.Status.DRAFT)
        self.assertEqual(
            tiers,
            [(5, 4000, True), (4, 3500, False), (3, 2500, False)],
        )
        self.assertEqual(DrawConfiguration.objects.count(), 1)
        self.assertEqual(Draw.objects.count(), 1)
