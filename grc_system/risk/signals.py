"""
Risk signals.

  * Route new risks and risk-acceptance requests to approval
    (status transitions are defined centrally in workflow/content.py).
  * Keep control-derived residual risk current: whenever a control's
    implementation status/effectiveness changes, or the set of controls
    linked to a risk changes, affected risks are recalculated.
  * Keep the risk-matrix threshold cache fresh.
"""
import logging

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

from compliance.models import ControlImplementation
from core.models import Setting
from workflow.content import submit_for_approval
from .models import Risk, RiskAcceptance
from . import utils as risk_utils

logger = logging.getLogger('grc.risk')


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


def _recalculate(risks):
    for risk in risks:
        try:
            risk.apply_control_based_residual(save=True)
        except Exception:
            logger.exception('Residual recalculation failed for risk %s', risk.pk)


@receiver(post_save, sender=ControlImplementation)
@receiver(post_delete, sender=ControlImplementation)
def recalculate_risks_for_control(sender, instance, **kwargs):
    """A control got (un)implemented or re-rated: refresh every linked risk in that organization."""
    _recalculate(Risk.objects.filter(organization_id=instance.organization_id, controls=instance.control_id,
                                     residual_auto=True).exclude(status='closed'))


@receiver(m2m_changed, sender=Risk.controls.through)
def recalculate_risk_on_control_link(sender, instance, action, reverse, **kwargs):
    """Controls were linked/unlinked to a risk."""
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if reverse:  # instance is a Control; refresh the risks on the other side
        _recalculate(Risk.objects.filter(controls=instance, residual_auto=True).exclude(status='closed'))
    elif getattr(instance, 'residual_auto', False):
        _recalculate([instance])
