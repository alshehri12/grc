"""
Risk app signals for workflow integration.
Auto-triggers workflows when authors create risks.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import Risk, RiskAcceptance

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


@receiver(post_save, sender=Risk)
def trigger_risk_workflow(sender, instance, created, **kwargs):
    """
    Trigger approval workflow when a risk is created.
    - If created by Author: needs manager approval
    - If created by Manager: auto-approve
    """
    from workflow.services import WorkflowService
    from workflow.models import WorkflowTemplate
    
    # Get creator - could be created_by or owner
    creator = getattr(instance, 'created_by', None) or instance.owner
    
    if not creator:
        return
    
    if created:
        is_author = user_is_author(creator)
        is_manager_user = user_is_manager(creator)
        
        if is_author and not is_manager_user:
            try:
                # Set status to pending approval
                if instance.status in ['identified', 'draft']:
                    Risk.objects.filter(pk=instance.pk).update(status='pending_approval')
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
                            creator
                        )
                        logger.info(f"Started approval workflow {workflow.pk} for risk {instance.risk_id}")
                        
            except Exception as e:
                logger.error(f"Error starting workflow for risk {instance.risk_id}: {e}")
        
        elif is_manager_user:
            try:
                Risk.objects.filter(pk=instance.pk).update(status='assessed')
                logger.info(f"Auto-approved risk {instance.risk_id} created by manager")
            except Exception as e:
                logger.error(f"Error auto-approving risk: {e}")


@receiver(post_save, sender=RiskAcceptance)
def trigger_risk_acceptance_workflow(sender, instance, created, **kwargs):
    """
    Trigger approval workflow for risk acceptance requests.
    """
    from workflow.services import WorkflowService
    from workflow.models import WorkflowTemplate
    
    if not instance.requested_by:
        return
    
    if created and instance.status == 'pending':
        try:
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
                        instance.requested_by
                    )
                    logger.info(f"Started workflow {workflow.pk} for risk acceptance {instance.pk}")
                    
        except Exception as e:
            logger.error(f"Error starting workflow for risk acceptance {instance.pk}: {e}")


# Connect workflow completion to update risk status
def handle_workflow_completed(sender, instance, **kwargs):
    """
    Update risk status when workflow completes.
    """
    if 'risk.risk' in instance.content_type:
        try:
            risk = Risk.objects.get(pk=instance.object_id)
            if instance.status == 'completed':
                risk.status = 'assessed'
            elif instance.status == 'rejected':
                risk.status = 'identified'
            risk.save(update_fields=['status'])
            logger.info(f"Updated risk {risk.risk_id} status to {risk.status}")
        except Risk.DoesNotExist:
            logger.warning(f"Risk not found for workflow completion: {instance.object_id}")
    
    elif 'risk.riskacceptance' in instance.content_type:
        try:
            acceptance = RiskAcceptance.objects.get(pk=instance.object_id)
            if instance.status == 'completed':
                acceptance.status = 'approved'
            elif instance.status == 'rejected':
                acceptance.status = 'rejected'
            acceptance.save(update_fields=['status'])
            logger.info(f"Updated risk acceptance {acceptance.pk} status to {acceptance.status}")
        except RiskAcceptance.DoesNotExist:
            logger.warning(f"RiskAcceptance not found for workflow completion: {instance.object_id}")


# Connect to workflow signals
from workflow.signals import workflow_completed
workflow_completed.connect(handle_workflow_completed)
