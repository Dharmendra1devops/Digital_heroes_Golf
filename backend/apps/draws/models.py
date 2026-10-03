from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import UUIDTimeStampedModel


class DrawConfiguration(UUIDTimeStampedModel):
    class Mode(models.TextChoices):
        RANDOM = 'random', 'Random'
        ALGORITHMIC = 'algorithmic', 'Algorithmic'

    version = models.PositiveIntegerField(unique=True)
    mode = models.CharField(max_length=12, choices=Mode.choices)
    candidate_min = models.PositiveSmallIntegerField(default=1)
    candidate_max = models.PositiveSmallIntegerField(default=45)
    number_count = models.PositiveSmallIntegerField(default=5)
    prize_pool_contribution_bps = models.PositiveSmallIntegerField(null=True, blank=True)
    parameters = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(candidate_max__gt=F('candidate_min')), name='draw_config_range_ck'),
            models.CheckConstraint(condition=Q(number_count__gt=0), name='draw_config_count_ck'),
            models.CheckConstraint(
                condition=(
                    Q(prize_pool_contribution_bps__isnull=True)
                    | Q(prize_pool_contribution_bps__lte=10000)
                ),
                name='draw_config_pool_pct_ck',
            ),
        ]

    def __str__(self):
        return f'Configuration v{self.version}'


class DrawPrizeTierConfiguration(UUIDTimeStampedModel):
    configuration = models.ForeignKey(DrawConfiguration, on_delete=models.CASCADE, related_name='prize_tiers')
    match_count = models.PositiveSmallIntegerField()
    share_bps = models.PositiveSmallIntegerField()
    rollover_unclaimed = models.BooleanField(default=False)

    class Meta:
        ordering = ('-match_count',)
        constraints = [
            models.UniqueConstraint(
                fields=('configuration', 'match_count'),
                name='draw_tier_config_match_uniq',
            ),
            models.CheckConstraint(condition=Q(match_count__in=(3, 4, 5)), name='draw_tier_config_match_ck'),
            models.CheckConstraint(condition=Q(share_bps__lte=10000), name='draw_tier_config_share_ck'),
        ]


class Draw(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SIMULATED = 'simulated', 'Simulated'
        PUBLISHED = 'published', 'Published'
        CANCELLED = 'cancelled', 'Cancelled'

    configuration = models.ForeignKey(DrawConfiguration, on_delete=models.PROTECT, related_name='draws')
    scheduled_at = models.DateTimeField()
    eligibility_cutoff = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    configuration_snapshot = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-scheduled_at',)
        indexes = [
            models.Index(fields=('status', 'scheduled_at'), name='draws_status_schedule_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(eligibility_cutoff__lte=F('scheduled_at')),
                name='draws_cutoff_before_run_ck',
            ),
        ]

    def __str__(self):
        return f'Draw {self.scheduled_at:%Y-%m-%d} ({self.status})'


class DrawRun(UUIDTimeStampedModel):
    class RunType(models.TextChoices):
        SIMULATION = 'simulation', 'Simulation'
        PUBLISH = 'publish', 'Publish'

    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name='runs')
    run_number = models.PositiveIntegerField()
    run_type = models.CharField(max_length=12, choices=RunType.choices)
    algorithm_version = models.CharField(max_length=40)
    input_hash = models.CharField(max_length=64, blank=True)
    input_snapshot = models.JSONField(default=dict, blank=True)
    result_snapshot = models.JSONField(default=dict, blank=True)
    audit_metadata = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ('draw', 'run_number')
        constraints = [
            models.UniqueConstraint(fields=('draw', 'run_number'), name='draw_run_number_uniq'),
            models.UniqueConstraint(
                fields=('draw',),
                condition=Q(is_published=True),
                name='draw_one_published_run_uniq',
            ),
            models.CheckConstraint(
                condition=Q(is_published=False) | Q(run_type='publish'),
                name='draw_published_run_type_ck',
            ),
        ]


class DrawEntry(UUIDTimeStampedModel):
    draw = models.ForeignKey(Draw, on_delete=models.PROTECT, related_name='entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='draw_entries')
    subscription = models.ForeignKey(
        'subscriptions.Subscription',
        on_delete=models.PROTECT,
        related_name='draw_entries',
    )
    eligible_at = models.DateTimeField()
    subscription_snapshot = models.JSONField(default=dict, blank=True)
    score_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('draw', 'user'), name='draw_entry_user_uniq'),
        ]
        indexes = [
            models.Index(fields=('user', 'draw'), name='draw_entry_user_draw_idx'),
        ]


class DrawEntryNumber(UUIDTimeStampedModel):
    entry = models.ForeignKey(DrawEntry, on_delete=models.CASCADE, related_name='numbers')
    ordinal = models.PositiveSmallIntegerField()
    number = models.PositiveSmallIntegerField()
    source_score = models.ForeignKey(
        'scores.GolfScore',
        on_delete=models.SET_NULL,
        related_name='draw_number_snapshots',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ('ordinal',)
        constraints = [
            models.UniqueConstraint(fields=('entry', 'ordinal'), name='draw_entry_number_pos_uniq'),
            models.CheckConstraint(condition=Q(number__gte=1, number__lte=45), name='draw_entry_number_ck'),
        ]


class DrawResultNumber(UUIDTimeStampedModel):
    run = models.ForeignKey(DrawRun, on_delete=models.CASCADE, related_name='winning_numbers')
    ordinal = models.PositiveSmallIntegerField()
    number = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('ordinal',)
        constraints = [
            models.UniqueConstraint(fields=('run', 'ordinal'), name='draw_result_number_pos_uniq'),
            models.CheckConstraint(condition=Q(number__gte=1, number__lte=45), name='draw_result_number_ck'),
        ]


class DrawTierPool(UUIDTimeStampedModel):
    draw = models.ForeignKey(Draw, on_delete=models.PROTECT, related_name='tier_pools')
    match_count = models.PositiveSmallIntegerField()
    share_bps = models.PositiveSmallIntegerField()
    available_minor = models.PositiveBigIntegerField(default=0)
    rollover_in_minor = models.PositiveBigIntegerField(default=0)
    rollover_out_minor = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('draw', 'match_count'), name='draw_pool_match_uniq'),
            models.CheckConstraint(condition=Q(match_count__in=(3, 4, 5)), name='draw_pool_match_ck'),
            models.CheckConstraint(condition=Q(share_bps__lte=10000), name='draw_pool_share_ck'),
        ]
