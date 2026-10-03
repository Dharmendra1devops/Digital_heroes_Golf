from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.charities.models import Charity, CharitySelection


@transaction.atomic
def select_charity(user, charity_id, contribution_bps):
    if not 1000 <= contribution_bps <= 10000:
        raise ValidationError({'contribution_bps': 'Contribution must be between 10% and 100%.'})

    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    charity = Charity.objects.get(pk=charity_id, is_active=True)
    current = (
        CharitySelection.objects.select_for_update()
        .filter(user=locked_user, effective_to__isnull=True)
        .first()
    )
    if current and current.charity_id == charity.pk and current.contribution_bps == contribution_bps:
        return current

    now = timezone.now()
    if current:
        current.effective_to = now
        current.save(update_fields=('effective_to', 'updated_at'))

    return CharitySelection.objects.create(
        user=locked_user,
        charity=charity,
        contribution_bps=contribution_bps,
        effective_from=now,
    )
