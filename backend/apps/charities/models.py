from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.common.models import UUIDTimeStampedModel


class Charity(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=160, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    image_path = models.CharField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('-is_featured', 'display_order', 'name')
        indexes = [
            models.Index(fields=('is_active', '-is_featured'), name='charities_active_featured_idx'),
        ]

    def __str__(self):
        return self.name


class CharityEvent(UUIDTimeStampedModel):
    charity = models.ForeignKey(Charity, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)
    image_path = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ('starts_at',)
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gte=F('starts_at')),
                name='charities_event_time_ck',
            ),
        ]

    def __str__(self):
        return self.title


class CharitySelection(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='charity_selections',
    )
    charity = models.ForeignKey(Charity, on_delete=models.PROTECT, related_name='selections')
    contribution_bps = models.PositiveSmallIntegerField(default=1000)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-effective_from',)
        constraints = [
            models.CheckConstraint(
                condition=Q(contribution_bps__gte=1000, contribution_bps__lte=10000),
                name='charity_selection_pct_ck',
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True) | Q(effective_to__gt=F('effective_from')),
                name='charity_selection_period_ck',
            ),
            models.UniqueConstraint(
                fields=('user',),
                condition=Q(effective_to__isnull=True),
                name='charity_one_current_sel_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=('user', '-effective_from'), name='charity_user_effective_idx'),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.charity.name}'
