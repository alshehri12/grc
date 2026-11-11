"""
Content approval rules shared by governance, risk, BCM and compliance.

Maker-checker principle: *every* newly created GRC item (policy, risk, plan,
audit ...) must be approved by someone other than its creator. Authors are
approved by their department manager; managers are approved by the next
manager up the hierarchy (see WorkflowService._resolve_assignee).

Each app's signals.py calls `submit_for_approval` on creation and the
single `handle_workflow_completed` receiver below applies the resulting
status when the workflow finishes.
"""
import logging

from django.apps import apps

logger = logging.getLogger('grc.workflow')

WORKFLOW_CODE = 'content-approval'

# content_type -> (statuses that trigger submission, pending status, approved status, rejected status)
CONTENT_RULES = {
    'governance.policy':         (('draft',),                'pending_approval', 'approved', 'draft'),
    'governance.procedure':      (('draft',),                'pending_approval', 'approved', 'draft'),
    'risk.risk':                 (('identified', 'draft'),   'pending_approval', 'identified', 'identified'),
    'risk.riskacceptance':       (('pending',),              'pending',          'approved', 'rejected'),
    'bcm.businessfunction':      (('active',),               'under_review',     'active',   'inactive'),
    'bcm.bcplan':                (('draft',),                'pending_approval', 'approved', 'draft'),
    'bcm.disasterrecoveryplan':  (('draft',),                'pending_approval', 'approved', 'draft'),
    'bcm.bcmtest':               (('planned',),              'planned',          'planned',  'cancelled'),
    'compliance.audit':          (('draft', 'planned'),      'pending_approval', 'planned',  'draft'),
}


def content_type_of(instance):
    return f'{instance._meta.app_label}.{instance._meta.model_name}'


def get_creator(instance):
    for attr in ('created_by', 'requested_by', 'owner', 'coordinator', 'lead_auditor'):
        user = getattr(instance, attr, None)
        if user:
            return user
    return None


def submit_for_approval(instance, creator=None):
    """
    Put a newly created item into the approval workflow.

    Returns the WorkflowInstance, or None when no workflow was started
    (no rule, no creator, template missing, or status not eligible).
    """
    from .models import WorkflowTemplate
    from .services import WorkflowService

    ct = content_type_of(instance)
    rule = CONTENT_RULES.get(ct)
    if not rule:
        return None
    trigger_statuses, pending_status, _, _ = rule

    creator = creator or get_creator(instance)
    if not creator:
        return None
    if instance.status not in trigger_statuses:
        return None

    try:
        if not WorkflowTemplate.objects.filter(code=WORKFLOW_CODE, is_active=True).exists():
            logger.debug('Content approval workflow template not found; %s left in %s', ct, instance.status)
            return None

        if WorkflowService.get_workflow_for_object(instance):
            return None

        if instance.status != pending_status:
            type(instance).objects.filter(pk=instance.pk).update(status=pending_status)
            instance.status = pending_status

        workflow = WorkflowService.start_workflow(WORKFLOW_CODE, instance, creator)
        logger.info('Started approval workflow %s for %s #%s', workflow.pk, ct, instance.pk)
        return workflow
    except Exception:
        logger.exception('Error starting approval workflow for %s #%s', ct, instance.pk)
        return None


def handle_workflow_completed(sender, instance, **kwargs):
    """Apply the approved/rejected status to the underlying object."""
    rule = CONTENT_RULES.get(instance.content_type)
    if not rule:
        return
    _, _, approved_status, rejected_status = rule

    try:
        app_label, model_name = instance.content_type.split('.')
        model = apps.get_model(app_label, model_name)
        obj = model.objects.filter(pk=instance.object_id).first()
        if not obj:
            logger.warning('%s #%s not found for workflow completion', instance.content_type, instance.object_id)
            return

        if instance.status == 'completed':
            new_status = approved_status
        elif instance.status == 'rejected':
            new_status = rejected_status
        else:
            return

        update = {'status': new_status}
        # Record who approved, where the model supports it.
        if instance.status == 'completed':
            approval = instance.approvals.filter(status='approved').order_by('-decided_at').first()
            if approval and approval.decided_by:
                if hasattr(obj, 'approved_by_id'):
                    update['approved_by'] = approval.decided_by
                if hasattr(obj, 'approved_date'):
                    update['approved_date'] = approval.decided_at.date() if approval.decided_at else None
        model.objects.filter(pk=obj.pk).update(**update)
        logger.info('Updated %s #%s status to %s', instance.content_type, obj.pk, new_status)
    except Exception:
        logger.exception('Error applying workflow result to %s #%s', instance.content_type, instance.object_id)
