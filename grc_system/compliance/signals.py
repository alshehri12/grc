"""
Compliance app signals for workflow integration.
Auto-triggers workflows when authors create compliance content.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import Audit

logger = logging.getLogger(__name__)


def user_is_author(user):
    """Check if user has the Author role."""
    if not user:
        return False
    try:
        profile = user.profile
        return profile.roles.filter(code='author').exists()
    except Exception:
        return False


def user_is_manager(user):
    """Check if user has the Manager role."""
    if not user:
        return False
    try:
        profile = user.profile
        return profile.roles.filter(code='manager').exists()
    except Exception:
        return False


def start_content_workflow(obj, creator, model_name, id_field='pk'):
    """Helper to start content approval workflow."""
    from workflow.services import WorkflowService
    from workflow.models import WorkflowTemplate
    
    try:
        template = WorkflowTemplate.objects.filter(
            code='content-approval',
            is_active=True
        ).first()
        
        if template:
            existing_workflow = WorkflowService.get_workflow_for_object(obj)
            
            if not existing_workflow:
                workflow = WorkflowService.start_workflow(
                    'content-approval',
                    obj,
                    creator
                )
                obj_id = getattr(obj, id_field, obj.pk)
                logger.info(f"Started approval workflow {workflow.pk} for {model_name} {obj_id}")
                return workflow
    except Exception as e:
        obj_id = getattr(obj, id_field, obj.pk)
        logger.error(f"Error starting workflow for {model_name} {obj_id}: {e}")
    return None


# Note: Control model doesn't have a status field - Controls are reference data
# Workflow approval is handled via ControlImplementation if needed


@receiver(post_save, sender=Audit)
def trigger_audit_workflow(sender, instance, created, **kwargs):
    """Trigger workflow when audit is created."""
    creator = getattr(instance, 'created_by', None) or instance.lead_auditor
    
    if not creator or not created:
        return
    
    is_author = user_is_author(creator)
    is_manager_user = user_is_manager(creator)
    
    if is_author and not is_manager_user:
        if instance.status in ['draft', 'planned']:
            Audit.objects.filter(pk=instance.pk).update(status='pending_approval')
            instance.refresh_from_db()
        start_content_workflow(instance, creator, 'Audit', 'audit_id')
    elif is_manager_user:
        Audit.objects.filter(pk=instance.pk).update(status='planned')
        logger.info(f"Auto-approved audit {instance.audit_id} by manager")


# Connect workflow completion to update compliance statuses
def handle_workflow_completed(sender, instance, **kwargs):
    """Update compliance content status when workflow completes."""
    
    if 'compliance.audit' in instance.content_type:
        try:
            obj = Audit.objects.get(pk=instance.object_id)
            obj.status = 'planned' if instance.status == 'completed' else 'draft'
            obj.save(update_fields=['status'])
            logger.info(f"Updated audit {obj.audit_id} status to {obj.status}")
        except Audit.DoesNotExist:
            pass


# Connect to workflow signals
from workflow.signals import workflow_completed
workflow_completed.connect(handle_workflow_completed)
