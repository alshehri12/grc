"""
Audit trail helpers.

`log_action` writes a core.AuditLog row; `AuditLogMixin` adds automatic
create/update/delete logging (with a field-level diff) to any DRF viewset.
Every GRC app's viewsets should extend `AuditedModelViewSet` so that all
API changes are traceable (NCA ECC 2-12 / ISO 27001 A.8.15).
"""
import logging

from django.db import models
from rest_framework import viewsets

from .models import AuditLog

logger = logging.getLogger('grc.audit')

# Fields that are never interesting in a diff.
_IGNORED_FIELDS = {'created_at', 'updated_at', 'password'}


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, models.Model):
        return value.pk
    return str(value)


def snapshot(instance):
    """Return {field_name: value} for all concrete (non-M2M) fields."""
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in _IGNORED_FIELDS:
            continue
        data[field.name] = _jsonable(getattr(instance, field.attname))
    return data


def diff(before, after):
    """Return {field: [old, new]} for every field whose value changed."""
    changes = {}
    for key, new in after.items():
        old = before.get(key)
        if old != new:
            changes[key] = [old, new]
    return changes


def content_type_label(instance):
    return f'{instance._meta.app_label}.{instance._meta.model_name}'


def log_action(user, action, instance=None, changes=None, request=None,
               content_type=None, object_id=None, object_repr=None):
    """
    Write an AuditLog entry. Never raises: an audit failure must not break
    the business operation (but is logged).
    """
    try:
        if instance is not None:
            content_type = content_type or content_type_label(instance)
            object_id = object_id if object_id is not None else instance.pk
            object_repr = object_repr or str(instance)
        return AuditLog.objects.create(
            user=user if (user and getattr(user, 'is_authenticated', False)) else None,
            action=action,
            content_type=content_type or '',
            object_id=str(object_id or ''),
            object_repr=(object_repr or '')[:500],
            changes=changes or {},
            ip_address=_client_ip(request),
            user_agent=(request.META.get('HTTP_USER_AGENT', '') if request else '')[:1000],
        )
    except Exception:  # pragma: no cover - defensive
        logger.exception('Failed to write audit log entry')
        return None


class AuditLogMixin:
    """Automatic audit logging for DRF model viewsets."""

    def perform_create(self, serializer):
        # Stamp the creator server-side so maker-checker rules can rely on it.
        extra = {}
        model = getattr(getattr(serializer, 'Meta', None), 'model', None)
        if model is not None and not serializer.validated_data.get('created_by'):
            if any(f.name == 'created_by' for f in model._meta.fields):
                extra['created_by'] = self.request.user
        instance = serializer.save(**extra)
        log_action(self.request.user, 'create', instance,
                   changes={'created': snapshot(instance)}, request=self.request)
        return instance

    def perform_update(self, serializer):
        before = snapshot(serializer.instance)
        instance = serializer.save()
        changes = diff(before, snapshot(instance))
        if changes:
            log_action(self.request.user, 'update', instance, changes=changes, request=self.request)
        return instance

    def perform_destroy(self, instance):
        log_action(self.request.user, 'delete', instance,
                   changes={'deleted': snapshot(instance)}, request=self.request)
        instance.delete()


class AuditedModelViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """ModelViewSet with automatic audit trail."""
