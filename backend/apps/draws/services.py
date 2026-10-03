from collections import Counter
from hashlib import sha256
import json
import random
import secrets

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.draws.models import Draw, DrawConfiguration, DrawEntry, DrawEntryNumber, DrawResultNumber, DrawRun
from apps.payments.models import SubscriptionInvoice
from apps.scores.models import GolfScore
from apps.subscriptions.models import Subscription


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
