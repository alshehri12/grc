"""
Risk signals: route new risks and risk-acceptance requests to approval,
and keep the risk-matrix threshold cache fresh.
Status transitions are defined centrally in workflow/content.py.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models import Setting
from workflow.content import submit_for_approval
from .models import Risk, RiskAcceptance
from . import utils as risk_utils


@receiver(post_save, sender=Risk)
def trigger_risk_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)


@receiver(post_save, sender=RiskAcceptance)
def trigger_risk_acceptance_workflow(sender, instance, created, **kwargs):
    if created:
        submit_for_approval(instance)


@receiver(post_save, sender=Setting)
@receiver(post_delete, sender=Setting)
def invalidate_risk_thresholds(sender, instance, **kwargs):
    if instance.key == risk_utils.THRESHOLD_SETTING_KEY:
        risk_utils.clear_threshold_cache()
