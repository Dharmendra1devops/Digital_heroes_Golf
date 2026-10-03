from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class GolfScore(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='golf_scores',
    )
    score_date = models.DateField()
    score = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('-score_date',)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=1, score__lte=45),
                name='scores_score_1_45_ck',
            ),
            models.UniqueConstraint(
                fields=('user', 'score_date'),
                name='scores_user_date_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=('user', '-score_date'), name='scores_user_date_desc_idx'),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.score} on {self.score_date}'
