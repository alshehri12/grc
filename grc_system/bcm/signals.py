"""
BCM signals.

  * Route new business functions, BC/DR plans and tests to approval
    (status transitions are defined centrally in workflow/content.py).
  * When an incident is linked to a risk, the risk owner gets a
    re-assessment task: a materialised risk is evidence that its likelihood
    (and possibly impact) must be reviewed.
"""
import logging
from datetime import timedelta

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from workflow.content import submit_for_approval
from .models import BusinessFunction, BCPlan, DisasterRecoveryPlan, BCMTest, CrisisIncident

logger = logging.getLogger('grc.bcm')


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


def request_risk_reassessment(risk, incident):
    """Create (once) a re-assessment task for the risk owner and notify them."""
    from workflow.models import Task
    from core.automation import notify_once

    owner = risk.owner
    if not owner:
        return None
    title = f'Re-assess risk {risk.risk_id} after incident {incident.incident_id}'
    existing = Task.objects.filter(content_type='risk.risk', object_id=risk.pk, task_type='assessment',
                                   status__in=['pending', 'in_progress', 'overdue']).first()
    if existing:
        return existing
    task = Task.objects.create(
        title=title, task_type='assessment', priority='high' if incident.severity in ('high', 'critical') else 'medium',
        description=(f"Incident {incident.incident_id} '{incident.title}' ({incident.get_severity_display()}) was linked to this risk. "
                     "Review the likelihood and impact scores, the effectiveness of the linked controls and the treatment plan."),
        assigned_to=owner, assigned_by=incident.reported_by, content_type='risk.risk', object_id=risk.pk,
        due_date=timezone.now() + timedelta(days=14),
    )
    notify_once(owner, f'Risk materialised: {risk.risk_id} {risk.title}',
                f"Incident {incident.incident_id} has been linked to risk {risk.risk_id}. A re-assessment task has been created.",
                'risk.risk', risk.pk, priority='high', dedupe_days=1, template_event='risk_assessment')
    return task


@receiver(m2m_changed, sender=CrisisIncident.related_risks.through)
def incident_linked_to_risk(sender, instance, action, reverse, pk_set, **kwargs):
    if action != 'post_add':
        return
    from risk.models import Risk
    if reverse:  # instance is a Risk; pk_set are incidents
        for incident in CrisisIncident.objects.filter(pk__in=pk_set):
            request_risk_reassessment(instance, incident)
    else:
        for risk in Risk.objects.filter(pk__in=pk_set).select_related('owner'):
            request_risk_reassessment(risk, instance)
