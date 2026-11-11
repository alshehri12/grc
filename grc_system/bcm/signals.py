"""
BCM signals: route new business functions, BC/DR plans and tests to approval.
Status transitions are defined centrally in workflow/content.py.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from workflow.content import submit_for_approval
from .models import BusinessFunction, BCPlan, DisasterRecoveryPlan, BCMTest


@receiver(post_save, sender=BusinessFunction)
def trigger_business_function_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)


@receiver(post_save, sender=BCPlan)
def trigger_bcplan_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)


@receiver(post_save, sender=DisasterRecoveryPlan)
def trigger_drplan_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)


@receiver(post_save, sender=BCMTest)
def trigger_bcmtest_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)
