from collections import Counter
from hashlib import sha256
import json
import random
import secrets
from uuid import NAMESPACE_URL, uuid5

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.charities.services import charity_selection_for_period
from apps.draws.models import (
    Draw,
    DrawConfiguration,
    DrawEntry,
    DrawEntryNumber,
    DrawResultNumber,
    DrawRun,
    DrawTierPool,
)
from apps.payments.models import FundingAllocation, SubscriptionInvoice
from apps.scores.models import GolfScore
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.winners.models import DrawWinner, Payout


@transaction.atomic
def simulate_draw(draw_id, seed=None):
    draw = Draw.objects.select_for_update().select_related('configuration').get(pk=draw_id)
    if draw.status in {Draw.Status.PUBLISHED, Draw.Status.CANCELLED}:
        raise ValidationError('Published or cancelled draws cannot be simulated.')

    configuration = draw.configuration
    candidate_numbers = list(range(configuration.candidate_min, configuration.candidate_max + 1))
    if configuration.number_count > len(candidate_numbers):
        raise ValidationError('The draw requests more numbers than its configured candidate range.')

    entries = list(DrawEntry.objects.filter(draw=draw).prefetch_related('numbers'))
    if not entries:
        subscriptions = (
            Subscription.objects.filter(
                status=Subscription.Status.ACTIVE,
                current_period_start__lte=draw.eligibility_cutoff,
                current_period_end__gt=draw.eligibility_cutoff,
                invoices__status=SubscriptionInvoice.Status.PAID,
                invoices__paid_at__lte=draw.eligibility_cutoff,
                invoices__period_start__lte=draw.eligibility_cutoff,
                invoices__period_end__gt=draw.eligibility_cutoff,
            )
            .select_related('plan')
            .order_by('user_id', '-current_period_end')
            .distinct()
        )
        seen_users = set()
        for subscription in subscriptions:
            if subscription.user_id in seen_users:
                continue
            scores = list(
                GolfScore.objects.filter(
                    user_id=subscription.user_id,
                    score_date__lte=draw.eligibility_cutoff.date(),
                ).order_by('-score_date')[:5]
            )
            if len(scores) != 5:
                continue

            invoice = subscription.invoices.filter(
                status=SubscriptionInvoice.Status.PAID,
                paid_at__lte=draw.eligibility_cutoff,
                period_start__lte=draw.eligibility_cutoff,
                period_end__gt=draw.eligibility_cutoff,
            ).order_by('-paid_at').first()
            if invoice is None:
                continue

            score_snapshot = [
                {'date': item.score_date.isoformat(), 'score': item.score}
                for item in scores
            ]
            entry = DrawEntry.objects.create(
                draw=draw,
                user_id=subscription.user_id,
                subscription=subscription,
                eligible_at=draw.eligibility_cutoff,
                subscription_snapshot={
                    'status': subscription.status,
                    'plan_interval': subscription.plan.interval,
                    'period_start': subscription.current_period_start.isoformat(),
                    'period_end': subscription.current_period_end.isoformat(),
                    'paid_invoice_id': invoice.stripe_invoice_id,
                },
                score_snapshot=score_snapshot,
            )
            DrawEntryNumber.objects.bulk_create([
                DrawEntryNumber(
                    entry=entry,
                    ordinal=ordinal,
                    number=item.score,
                    source_score=item,
                )
                for ordinal, item in enumerate(scores, start=1)
            ])
            seen_users.add(subscription.user_id)

        entries = list(DrawEntry.objects.filter(draw=draw).prefetch_related('numbers'))

    if not entries:
        raise ValidationError('No paid subscribers with five eligible scores qualify for this draw.')

    entry_values = {
        str(entry.pk): [number.number for number in entry.numbers.all()]
        for entry in entries
    }
    parameters = configuration.parameters or {}
    match_policy = parameters.get('duplicate_score_match_policy', 'unique')
    if match_policy not in {'unique', 'frequency'}:
        raise ValidationError('duplicate_score_match_policy must be unique or frequency.')

    rng_seed = seed or secrets.token_hex(16)
    generator = random.Random(rng_seed)
    if configuration.mode == DrawConfiguration.Mode.ALGORITHMIC:
        frequencies = Counter(
            number
            for values in entry_values.values()
            for number in values
            if number in candidate_numbers
        )
        remaining_numbers = candidate_numbers[:]
        winning_numbers = []
        for _ in range(configuration.number_count):
            weights = [max(1, frequencies.get(number, 0)) for number in remaining_numbers]
            selected = generator.choices(remaining_numbers, weights=weights, k=1)[0]
            winning_numbers.append(selected)
            remaining_numbers.remove(selected)
    else:
        winning_numbers = generator.sample(candidate_numbers, configuration.number_count)

    winning_set = set(winning_numbers)
    matches = []
    for entry_id, values in entry_values.items():
        if match_policy == 'frequency':
            match_count = sum((Counter(values) & Counter(winning_numbers)).values())
        else:
            match_count = len(set(values) & winning_set)
        matches.append({'entry_id': entry_id, 'match_count': match_count})

    input_snapshot = {
        'draw_id': str(draw.pk),
        'configuration_version': configuration.version,
        'configuration': {
            'mode': configuration.mode,
            'candidate_min': configuration.candidate_min,
            'candidate_max': configuration.candidate_max,
            'number_count': configuration.number_count,
            'prize_pool_contribution_bps': configuration.prize_pool_contribution_bps,
            'prize_tiers': list(
                configuration.prize_tiers.order_by('-match_count').values(
                    'match_count',
                    'share_bps',
                    'rollover_unclaimed',
                )
            ),
        },
        'entries': [
            {'entry_id': entry_id, 'numbers': values}
            for entry_id, values in sorted(entry_values.items())
        ],
    }
    input_hash = sha256(
        json.dumps(input_snapshot, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    run_number = (DrawRun.objects.filter(draw=draw).order_by('-run_number').values_list('run_number', flat=True).first() or 0) + 1
    run = DrawRun.objects.create(
        draw=draw,
        run_number=run_number,
        run_type=DrawRun.RunType.SIMULATION,
        algorithm_version=f'{configuration.mode}-v1',
        input_hash=input_hash,
        input_snapshot=input_snapshot,
        result_snapshot={
            'winning_numbers': winning_numbers,
            'matches': matches,
            'eligible_entry_count': len(entries),
        },
        audit_metadata={
            'seed': rng_seed,
            'score_match_policy': match_policy,
            'simulated_at': draw.updated_at.isoformat(),
        },
    )
    DrawResultNumber.objects.bulk_create([
        DrawResultNumber(run=run, ordinal=ordinal, number=number)
        for ordinal, number in enumerate(winning_numbers, start=1)
    ])
    draw.status = Draw.Status.SIMULATED
    draw.save(update_fields=('status', 'updated_at'))
    return run


def _allocate_pool(total_minor, tiers):
    amounts = {
        tier['match_count']: total_minor * tier['share_bps'] // 10000
        for tier in tiers
    }
    remainder = total_minor - sum(amounts.values())
    ordered_tiers = sorted(
        tiers,
        key=lambda tier: (
            -(total_minor * tier['share_bps'] % 10000),
            -tier['match_count'],
        ),
    )
    for tier in ordered_tiers[:remainder]:
        amounts[tier['match_count']] += 1
    return amounts


@transaction.atomic
def publish_draw(draw_id, published_by):
    draw = (
        Draw.objects.select_for_update()
        .select_related('configuration')
        .get(pk=draw_id)
    )
    if draw.status != Draw.Status.SIMULATED:
        raise ValidationError('Only a simulated draw can be published.')
    if DrawWinner.objects.filter(entry__draw=draw).exists():
        raise ValidationError('This draw already has winner records.')
    if Draw.objects.filter(
        scheduled_at__lt=draw.scheduled_at,
        status__in=(Draw.Status.DRAFT, Draw.Status.SIMULATED),
    ).exists():
        raise ValidationError('Earlier draws must be published or cancelled first.')

    simulation = (
        DrawRun.objects.select_for_update()
        .filter(draw=draw, run_type=DrawRun.RunType.SIMULATION)
        .order_by('-run_number')
        .first()
    )
    if simulation is None:
        raise ValidationError('A completed simulation is required before publication.')

    input_snapshot = simulation.input_snapshot
    entries_snapshot = input_snapshot.get('entries', [])
    result_snapshot = simulation.result_snapshot
    winning_numbers = result_snapshot.get('winning_numbers', [])
    configuration = input_snapshot.get('configuration')
    if not configuration:
        configuration = {
            'mode': draw.configuration.mode,
            'candidate_min': draw.configuration.candidate_min,
            'candidate_max': draw.configuration.candidate_max,
            'number_count': draw.configuration.number_count,
            'prize_pool_contribution_bps': draw.configuration.prize_pool_contribution_bps,
            'prize_tiers': list(
                draw.configuration.prize_tiers.order_by('-match_count').values(
                    'match_count',
                    'share_bps',
                    'rollover_unclaimed',
                )
            ),
        }
    if (
        len(winning_numbers) != configuration.get('number_count')
        or len(set(winning_numbers)) != len(winning_numbers)
        or any(
            not configuration.get('candidate_min', 1) <= number <= configuration.get('candidate_max', 0)
            for number in winning_numbers
        )
    ):
        raise ValidationError('The simulation does not contain winning numbers.')

    entries = {
        str(entry.pk): entry
        for entry in DrawEntry.objects.filter(draw=draw).select_related('subscription__plan')
    }
    snapshot_entry_ids = {item.get('entry_id') for item in entries_snapshot}
    matches_by_entry = {
        item.get('entry_id'): item.get('match_count')
        for item in result_snapshot.get('matches', [])
    }
    if (
        not entries
        or snapshot_entry_ids != set(entries)
        or set(matches_by_entry) != set(entries)
    ):
        raise ValidationError('The simulation entry snapshot is incomplete or has changed.')

    contribution_bps = configuration.get('prize_pool_contribution_bps')
    if not isinstance(contribution_bps, int) or not 1 <= contribution_bps <= 10000:
        raise ValidationError('Configure a positive prize-pool contribution before publishing.')

    tiers = configuration.get('prize_tiers', [])
    expected_tier_shares = {3: 2500, 4: 3500, 5: 4000}
    if (
        len(tiers) != 3
        or {tier.get('match_count') for tier in tiers} != {3, 4, 5}
        or {
            tier.get('match_count'): tier.get('share_bps')
            for tier in tiers
        } != expected_tier_shares
        or any(
            tier.get('rollover_unclaimed') != (tier.get('match_count') == 5)
            for tier in tiers
        )
    ):
        raise ValidationError('Prize tiers must use the required 25% / 35% / 40% shares and jackpot rollover.')

    subscriptions = (
        Subscription.objects.filter(
            status=Subscription.Status.ACTIVE,
            current_period_start__lte=draw.eligibility_cutoff,
            current_period_end__gt=draw.eligibility_cutoff,
            invoices__status=SubscriptionInvoice.Status.PAID,
            invoices__paid_at__lte=draw.eligibility_cutoff,
            invoices__period_start__lte=draw.eligibility_cutoff,
            invoices__period_end__gt=draw.eligibility_cutoff,
        )
        .select_related('plan')
        .order_by('user_id', '-current_period_end')
        .distinct()
    )
    seen_users = set()
    invoices = []
    for subscription in subscriptions:
        if subscription.user_id in seen_users:
            continue
        invoice = (
            SubscriptionInvoice.objects.select_for_update()
            .select_related('subscription__plan')
            .filter(
                subscription=subscription,
                status=SubscriptionInvoice.Status.PAID,
                paid_at__lte=draw.eligibility_cutoff,
                period_start__lte=draw.eligibility_cutoff,
                period_end__gt=draw.eligibility_cutoff,
            )
            .order_by('-paid_at')
            .first()
        )
        if invoice is None:
            continue
        invoices.append(invoice)
        seen_users.add(subscription.user_id)
    if not invoices:
        raise ValidationError('No active subscribers with a paid invoice qualify to fund this draw.')

    if any(
        not isinstance(matches_by_entry[entry_id], int)
        or not 0 <= matches_by_entry[entry_id] <= configuration.get('number_count', 0)
        for entry_id in entries
    ):
        raise ValidationError('The simulation contains an invalid match count.')

    currencies = {invoice.currency.upper() for invoice in invoices}
    if len(currencies) != 1:
        raise ValidationError('A draw cannot settle prize pools in multiple currencies.')
    currency = currencies.pop()

    total_contribution_minor = 0
    for invoice in invoices:
        charity_selection = charity_selection_for_period(
            invoice.subscription.user_id,
            invoice.period_start or invoice.paid_at,
        )
        if (
            charity_selection is not None
            and contribution_bps + charity_selection.contribution_bps > 10000
        ):
            raise ValidationError(
                'The prize-pool and selected charity contributions cannot exceed the subscription payment.'
            )
        contribution_basis = invoice.amount_minor
        if invoice.subscription.plan.interval == SubscriptionPlan.Interval.YEARLY:
            contribution_basis //= 12
        contribution_minor = contribution_basis * contribution_bps // 10000
        if contribution_minor == 0:
            continue
        idempotency_key = uuid5(
            NAMESPACE_URL,
            f'draw-prize-allocation:{draw.pk}:{invoice.pk}',
        )
        allocation = FundingAllocation.objects.select_for_update().filter(
            idempotency_key=idempotency_key,
        ).first()
        if allocation is None:
            allocation = FundingAllocation.objects.create(
                invoice=invoice,
                draw=draw,
                allocation_type=FundingAllocation.Type.PRIZE_POOL,
                amount_minor=contribution_minor,
                currency=currency,
                idempotency_key=idempotency_key,
            )
        if (
            allocation.invoice_id != invoice.pk
            or allocation.draw_id != draw.pk
            or allocation.allocation_type != FundingAllocation.Type.PRIZE_POOL
            or allocation.amount_minor != contribution_minor
            or allocation.currency != currency
        ):
            raise ValidationError('An existing prize-pool allocation conflicts with this draw.')
        total_contribution_minor += allocation.amount_minor

    if total_contribution_minor <= 0:
        raise ValidationError('The eligible paid invoices do not provide a positive prize pool.')

    tier_contributions = _allocate_pool(total_contribution_minor, tiers)
    if DrawTierPool.objects.filter(draw=draw).exists():
        raise ValidationError('This draw already has prize-pool records.')

    previous_draw_pools = {
        pool.match_count: pool
        for pool in DrawTierPool.objects.select_for_update()
        .filter(
            draw__scheduled_at__lt=draw.scheduled_at,
            draw__status=Draw.Status.PUBLISHED,
        )
        .order_by('draw__scheduled_at')
    }
    for tier in tiers:
        match_count = tier['match_count']
        previous_pool = previous_draw_pools.get(match_count)
        rollover_in_minor = 0
        if previous_pool is not None:
            rollover_in_minor = previous_pool.rollover_out_minor
            if rollover_in_minor and previous_pool.currency != currency:
                raise ValidationError('A rollover cannot move between currencies.')
        available_minor = tier_contributions[match_count] + rollover_in_minor
        tier_winners = sorted(
            (
                entry
                for entry_id, entry in entries.items()
                if matches_by_entry[entry_id] == match_count
            ),
            key=lambda entry: str(entry.user_id),
        )
        if tier_winners and available_minor < len(tier_winners):
            raise ValidationError(
                f'The {match_count}-match pool cannot award at least one minor unit to every winner.'
            )
        rollover_out_minor = (
            available_minor
            if not tier_winners and tier['rollover_unclaimed']
            else 0
        )
        DrawTierPool.objects.create(
            draw=draw,
            match_count=match_count,
            share_bps=tier['share_bps'],
            available_minor=available_minor,
            rollover_in_minor=rollover_in_minor,
            rollover_out_minor=rollover_out_minor,
            currency=currency,
        )
        if tier_winners:
            base_prize, extra_minor_units = divmod(available_minor, len(tier_winners))
            for index, entry in enumerate(tier_winners):
                prize_minor = base_prize + (index < extra_minor_units)
                winner = DrawWinner.objects.create(
                    entry=entry,
                    match_count=match_count,
                    prize_amount_minor=prize_minor,
                    currency=currency,
                )
                Payout.objects.create(
                    winner=winner,
                    attempt_number=1,
                    amount_minor=prize_minor,
                    currency=currency,
                )

    published_at = timezone.now()
    publication_snapshot = {
        'version': input_snapshot.get('configuration_version'),
        **configuration,
    }
    draw.configuration_snapshot = publication_snapshot
    draw.status = Draw.Status.PUBLISHED
    draw.published_at = published_at
    draw.save(update_fields=('configuration_snapshot', 'status', 'published_at', 'updated_at'))

    pool_records = list(draw.tier_pools.order_by('-match_count'))
    published_results = {
        **result_snapshot,
        'currency': currency,
        'contributions_minor': total_contribution_minor,
        'total_pool_minor': sum(pool.available_minor for pool in pool_records),
        'winner_count': DrawWinner.objects.filter(entry__draw=draw).count(),
        'prize_pools': [
            {
                'match_count': pool.match_count,
                'share_bps': pool.share_bps,
                'available_minor': pool.available_minor,
                'rollover_in_minor': pool.rollover_in_minor,
                'rollover_out_minor': pool.rollover_out_minor,
                'currency': pool.currency,
            }
            for pool in pool_records
        ],
    }
    run_number = (
        DrawRun.objects.filter(draw=draw)
        .order_by('-run_number')
        .values_list('run_number', flat=True)
        .first()
        or 0
    ) + 1
    publish_run = DrawRun.objects.create(
        draw=draw,
        run_number=run_number,
        run_type=DrawRun.RunType.PUBLISH,
        algorithm_version=simulation.algorithm_version,
        input_hash=simulation.input_hash,
        input_snapshot=input_snapshot,
        result_snapshot=published_results,
        audit_metadata={
            'simulation_run_id': str(simulation.pk),
            'published_at': published_at.isoformat(),
            'published_by': str(published_by.pk),
            'funding_allocation_ids': [
                str(allocation.pk)
                for allocation in FundingAllocation.objects.filter(draw=draw).order_by('created_at')
            ],
        },
        is_published=True,
    )
    DrawResultNumber.objects.bulk_create([
        DrawResultNumber(run=publish_run, ordinal=ordinal, number=number)
        for ordinal, number in enumerate(winning_numbers, start=1)
    ])
    return publish_run
