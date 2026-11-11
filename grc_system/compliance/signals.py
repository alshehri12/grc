"""
Compliance signals: route new audits to approval.
Status transitions are defined centrally in workflow/content.py.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from workflow.content import submit_for_approval
from .models import Audit


@receiver(post_save, sender=Audit)
def trigger_audit_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)
