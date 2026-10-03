from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.common.models import UUIDTimeStampedModel


class UserProfile(UUIDTimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    email = models.EmailField(max_length=254)
    display_name = models.CharField(max_length=120, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower('email'), name='accounts_profile_email_ci_uniq'),
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
