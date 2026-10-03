import uuid

from django.conf import settings
from django.db import models


class UUIDTimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AdminAuditEvent(UUIDTimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='admin_audit_events',
    )
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=100)
    target_id = models.UUIDField(null=True, blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('actor', '-created_at'), name='common_audit_actor_idx'),
            models.Index(fields=('target_type', 'target_id'), name='common_audit_target_idx'),
        ]

    def __str__(self):
        return f'{self.action} {self.target_type}'
