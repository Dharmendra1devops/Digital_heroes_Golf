from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import UUIDTimeStampedModel


class DrawWinner(UUIDTimeStampedModel):
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    entry = models.ForeignKey('draws.DrawEntry', on_delete=models.PROTECT, related_name='winners')
    match_count = models.PositiveSmallIntegerField()
    prize_amount_minor = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3)
    verification_status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviewed_winners',
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('entry', 'match_count'), name='winner_entry_match_uniq'),
            models.CheckConstraint(condition=Q(match_count__in=(3, 4, 5)), name='winner_match_count_ck'),
        ]
        indexes = [
            models.Index(fields=('verification_status', 'created_at'), name='winner_verification_idx'),
        ]


class WinnerProof(UUIDTimeStampedModel):
    class ReviewStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    winner = models.ForeignKey(DrawWinner, on_delete=models.PROTECT, related_name='proofs')
    bucket = models.CharField(max_length=100, default='winner-proofs')
    object_path = models.CharField(max_length=500)
    review_status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviewed_winner_proofs',
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.TextField(blank=True)

    class Meta:
        ordering = ('-submitted_at',)
        indexes = [
            models.Index(fields=('review_status', 'submitted_at'), name='winner_proof_review_idx'),
        ]


class Payout(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'

    winner = models.ForeignKey(DrawWinner, on_delete=models.PROTECT, related_name='payouts')
    attempt_number = models.PositiveSmallIntegerField(default=1)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    provider_payout_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ('winner', 'attempt_number')
        constraints = [
            models.UniqueConstraint(fields=('winner', 'attempt_number'), name='payout_winner_attempt_uniq'),
            models.CheckConstraint(condition=Q(amount_minor__gt=0), name='payout_amount_pos_ck'),
        ]
