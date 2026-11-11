"""
Governance signals: route newly created policies/procedures to approval.
Status transitions are defined centrally in workflow/content.py.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from workflow.content import submit_for_approval
from .models import Policy, Procedure


@receiver(post_save, sender=Policy)
def trigger_policy_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)


@receiver(post_save, sender=Procedure)
def trigger_procedure_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)
