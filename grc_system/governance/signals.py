"""
Governance app signals for workflow integration.
Auto-triggers workflows when authors create policies/procedures.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from .models import Policy, Procedure

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


def get_user_manager(user):
    """Get the manager of the user's department."""
    if not user:
        return None
    try:
        profile = user.profile
        if profile.department and profile.department.manager:
            return profile.department.manager
    except Exception:
        pass
    return None


@receiver(post_save, sender=Policy)
def trigger_policy_workflow(sender, instance, created, **kwargs):
    """
    Trigger approval workflow when a policy is created or submitted.
    - If created by Author: auto-set to pending_approval and start workflow
    - If created by Manager: auto-approve
    """
    from workflow.services import WorkflowService
    from workflow.models import WorkflowTemplate
    
    # Skip if no created_by (bulk operations, migrations, etc.)
    if not instance.created_by:
        return
    
    # Only trigger on new creation or when explicitly submitted
    if created:
        is_author = user_is_author(instance.created_by)
        is_manager_user = user_is_manager(instance.created_by)
        
        if is_author and not is_manager_user:
            # Author created - needs manager approval
            try:
                # Set status to pending approval
                if instance.status == 'draft':
                    Policy.objects.filter(pk=instance.pk).update(status='pending_approval')
                    instance.refresh_from_db()
                
                # Check if workflow template exists
                template = WorkflowTemplate.objects.filter(
                    code='content-approval',
                    is_active=True
                ).first()
                
                if template:
                    # Check if workflow already exists
                    existing_workflow = WorkflowService.get_workflow_for_object(instance)
                    
                    if not existing_workflow:
                        workflow = WorkflowService.start_workflow(
                            'content-approval',
                            instance,
                            instance.created_by
                        )
                        logger.info(f"Started approval workflow {workflow.pk} for policy {instance.policy_id}")
                else:
                    logger.debug("Content approval workflow template not found")
                    
            except Exception as e:
                logger.error(f"Error starting workflow for policy {instance.policy_id}: {e}")
        
        elif is_manager_user:
            # Manager created - auto-approve
            try:
                Policy.objects.filter(pk=instance.pk).update(status='approved')
                logger.info(f"Auto-approved policy {instance.policy_id} created by manager")
            except Exception as e:
                logger.error(f"Error auto-approving policy: {e}")


@receiver(post_save, sender=Procedure)
def trigger_procedure_workflow(sender, instance, created, **kwargs):
    """
    Trigger approval workflow when a procedure is created.
    """
    from workflow.services import WorkflowService
    from workflow.models import WorkflowTemplate
    
    if not instance.created_by:
        return
    
    if created:
        is_author = user_is_author(instance.created_by)
        is_manager_user = user_is_manager(instance.created_by)
        
        if is_author and not is_manager_user:
            try:
                if instance.status == 'draft':
                    Procedure.objects.filter(pk=instance.pk).update(status='pending_approval')
                    instance.refresh_from_db()
                
                template = WorkflowTemplate.objects.filter(
                    code='content-approval',
                    is_active=True
                ).first()
                
                if template:
                    existing_workflow = WorkflowService.get_workflow_for_object(instance)
                    
                    if not existing_workflow:
                        workflow = WorkflowService.start_workflow(
                            'content-approval',
                            instance,
                            instance.created_by
                        )
                        logger.info(f"Started approval workflow {workflow.pk} for procedure {instance.procedure_id}")
                        
            except Exception as e:
                logger.error(f"Error starting workflow for procedure {instance.procedure_id}: {e}")
        
        elif is_manager_user:
            try:
                Procedure.objects.filter(pk=instance.pk).update(status='approved')
                logger.info(f"Auto-approved procedure {instance.procedure_id} created by manager")
            except Exception as e:
                logger.error(f"Error auto-approving procedure: {e}")


# Connect workflow completion to update status
def handle_workflow_completed(sender, instance, **kwargs):
    """
    Update policy/procedure status when workflow completes.
    """
    if 'governance.policy' in instance.content_type:
        try:
            policy = Policy.objects.get(pk=instance.object_id)
            if instance.status == 'completed':
                policy.status = 'approved'
            elif instance.status == 'rejected':
                policy.status = 'draft'
            policy.save(update_fields=['status'])
            logger.info(f"Updated policy {policy.policy_id} status to {policy.status}")
        except Policy.DoesNotExist:
            logger.warning(f"Policy not found for workflow completion: {instance.object_id}")
    
    elif 'governance.procedure' in instance.content_type:
        try:
            procedure = Procedure.objects.get(pk=instance.object_id)
            if instance.status == 'completed':
                procedure.status = 'approved'
            elif instance.status == 'rejected':
                procedure.status = 'draft'
            procedure.save(update_fields=['status'])
            logger.info(f"Updated procedure {procedure.procedure_id} status to {procedure.status}")
        except Procedure.DoesNotExist:
            logger.warning(f"Procedure not found for workflow completion: {instance.object_id}")


# Connect to workflow signals
from workflow.signals import workflow_completed
workflow_completed.connect(handle_workflow_completed)
