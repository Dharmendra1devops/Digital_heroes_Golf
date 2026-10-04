from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.draws.models import (
    Draw,
    DrawConfiguration,
    DrawPrizeTierConfiguration,
)


SEED_KEY = 'portfolio-example-draw'
PRIZE_TIERS = (
    (5, 4000, True),
    (4, 3500, False),
    (3, 2500, False),
)


class Command(BaseCommand):
    help = 'Create an unpublished example draw for the administrator walkthrough.'

    @transaction.atomic
    def handle(self, *args, **options):
        configuration = DrawConfiguration.objects.filter(
            parameters__seed_key=SEED_KEY,
        ).first()
        if configuration is None:
            version = (DrawConfiguration.objects.order_by('-version').values_list('version', flat=True).first() or 0) + 1
            configuration = DrawConfiguration.objects.create(
                version=version,
                mode=DrawConfiguration.Mode.RANDOM,
                candidate_min=1,
                candidate_max=45,
                number_count=5,
                prize_pool_contribution_bps=None,
                parameters={
                    'seed_key': SEED_KEY,
                    'duplicate_score_match_policy': 'unique',
                },
            )
            self.stdout.write(f'Created configuration v{configuration.version}')
        else:
            self.stdout.write(f'Kept configuration v{configuration.version}')

        for match_count, share_bps, rollover in PRIZE_TIERS:
            DrawPrizeTierConfiguration.objects.get_or_create(
                configuration=configuration,
                match_count=match_count,
                defaults={
                    'share_bps': share_bps,
                    'rollover_unclaimed': rollover,
                },
            )

        draw = Draw.objects.filter(configuration=configuration).order_by('created_at').first()
        if draw is None:
            scheduled_at = timezone.now().replace(second=0, microsecond=0) + timedelta(days=7)
            draw = Draw.objects.create(
                configuration=configuration,
                scheduled_at=scheduled_at,
                eligibility_cutoff=scheduled_at - timedelta(days=1),
            )
            self.stdout.write(f'Created unpublished draft scheduled for {draw.scheduled_at.isoformat()}')
        else:
            self.stdout.write(f'Kept existing draw in {draw.status} status')

        self.stdout.write(self.style.SUCCESS(
            'Example draw setup is ready. Set and approve a prize contribution before publishing.'
        ))
