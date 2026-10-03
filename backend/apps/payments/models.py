from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import UUIDTimeStampedModel


class StripeCustomer(UUIDTimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='stripe_customer',
    )
    stripe_customer_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f'{self.user_id}: {self.stripe_customer_id}'


class SubscriptionInvoice(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'
        UNCOLLECTIBLE = 'uncollectible', 'Uncollectible'

    subscription = models.ForeignKey(
        'subscriptions.Subscription',
        on_delete=models.PROTECT,
        related_name='invoices',
    )
    stripe_invoice_id = models.CharField(max_length=100, unique=True)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.CheckConstraint(condition=Q(amount_minor__gte=0), name='payments_invoice_amount_ck'),
            models.CheckConstraint(
                condition=(
                    Q(period_start__isnull=True)
                    | Q(period_end__isnull=True)
                    | Q(period_end__gt=F('period_start'))
                ),
                name='payments_invoice_period_ck',
            ),
        ]


class StripeWebhookEvent(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        RECEIVED = 'received', 'Received'
        PROCESSING = 'processing', 'Processing'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'

    stripe_event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECEIVED)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ('-received_at',)


class Donation(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='donations',
        null=True,
        blank=True,
    )
    charity = models.ForeignKey('charities.Charity', on_delete=models.PROTECT, related_name='donations')
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount_minor__gt=0), name='payments_donation_amount_ck'),
        ]


class FundingAllocation(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        PRIZE_POOL = 'prize_pool', 'Prize pool'
        CHARITY = 'charity', 'Charity'
        PLATFORM = 'platform', 'Platform'

    invoice = models.ForeignKey(SubscriptionInvoice, on_delete=models.PROTECT, related_name='allocations')
    draw = models.ForeignKey(
        'draws.Draw',
        on_delete=models.PROTECT,
        related_name='funding_allocations',
        null=True,
        blank=True,
    )
    charity_selection = models.ForeignKey(
        'charities.CharitySelection',
        on_delete=models.PROTECT,
        related_name='funding_allocations',
        null=True,
        blank=True,
    )
    allocation_type = models.CharField(max_length=12, choices=Type.choices)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)
    idempotency_key = models.UUIDField(unique=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount_minor__gt=0), name='payments_allocation_amount_ck'),
        ]
