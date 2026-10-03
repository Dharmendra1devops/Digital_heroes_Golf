from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import UUIDTimeStampedModel


class SubscriptionPlan(UUIDTimeStampedModel):
    class Interval(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    interval = models.CharField(max_length=10, choices=Interval.choices, unique=True)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)
    stripe_price_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount_minor__gt=0), name='subs_plan_amount_pos_ck'),
        ]

    def __str__(self):
        return f'{self.get_interval_display()} ({self.currency})'


class Subscription(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        INCOMPLETE = 'incomplete', 'Incomplete'
        INCOMPLETE_EXPIRED = 'incomplete_expired', 'Incomplete expired'
        TRIALING = 'trialing', 'Trialing'
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past due'
        CANCELED = 'canceled', 'Canceled'
        UNPAID = 'unpaid', 'Unpaid'
        PAUSED = 'paused', 'Paused'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='subscriptions',
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    stripe_subscription_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.INCOMPLETE)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=('user', 'status', 'current_period_end'), name='subs_user_status_period_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(current_period_start__isnull=True)
                    | Q(current_period_end__isnull=True)
                    | Q(current_period_end__gt=F('current_period_start'))
                ),
                name='subs_period_order_ck',
            ),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.status}'
