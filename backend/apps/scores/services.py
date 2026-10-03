from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from uuid import UUID

from apps.scores.models import GolfScore


@transaction.atomic
def save_golf_score(user: AbstractBaseUser, score_date: date, score: int) -> GolfScore:
    if not 1 <= score <= 45:
        raise ValidationError({'score': 'Stableford scores must be between 1 and 45.'})

    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    score_record, _created = GolfScore.objects.update_or_create(
        user=locked_user,
        score_date=score_date,
        defaults={'score': score},
    )

    retained_ids = list(
        GolfScore.objects.filter(user=locked_user)
        .order_by('-score_date')
        .values_list('pk', flat=True)[:5]
    )
    if score_record.pk not in retained_ids:
        raise ValidationError({'score_date': 'Only the five most recent dated scores can be retained.'})

    GolfScore.objects.filter(user=locked_user).exclude(pk__in=retained_ids).delete()
    return score_record


@transaction.atomic
def delete_golf_score(user: AbstractBaseUser, score_id: UUID) -> bool:
    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    deleted, _details = GolfScore.objects.filter(user=locked_user, pk=score_id).delete()
    return deleted > 0
