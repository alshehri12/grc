"""
BCM app signals for workflow integration.
Auto-triggers workflows when authors create BCM content.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import BusinessFunction, BCPlan, DisasterRecoveryPlan, BCMTest

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


@receiver(post_save, sender=BusinessFunction)
def trigger_business_function_workflow(sender, instance, created, **kwargs):
    """Trigger workflow when business function is created."""
    creator = getattr(instance, 'created_by', None) or instance.owner
    
    if not creator or not created:
        return
    
    is_author = user_is_author(creator)
    is_manager_user = user_is_manager(creator)
    
    if is_author and not is_manager_user:
        if instance.status in ['draft', 'active']:
            BusinessFunction.objects.filter(pk=instance.pk).update(status='pending_approval')
            instance.refresh_from_db()
        start_content_workflow(instance, creator, 'BusinessFunction', 'function_id')
    elif is_manager_user:
        BusinessFunction.objects.filter(pk=instance.pk).update(status='active')
        logger.info(f"Auto-approved business function {instance.function_id} by manager")


@receiver(post_save, sender=BCPlan)
def trigger_bcplan_workflow(sender, instance, created, **kwargs):
    """Trigger workflow when BC plan is created."""
    creator = getattr(instance, 'created_by', None) or instance.owner
    
    if not creator or not created:
        return
    
    is_author = user_is_author(creator)
    is_manager_user = user_is_manager(creator)
    
    if is_author and not is_manager_user:
        if instance.status in ['draft']:
            BCPlan.objects.filter(pk=instance.pk).update(status='pending_approval')
            instance.refresh_from_db()
        start_content_workflow(instance, creator, 'BCPlan', 'plan_id')
    elif is_manager_user:
        BCPlan.objects.filter(pk=instance.pk).update(status='approved')
        logger.info(f"Auto-approved BC plan {instance.plan_id} by manager")


@receiver(post_save, sender=DisasterRecoveryPlan)
def trigger_drplan_workflow(sender, instance, created, **kwargs):
    """Trigger workflow when DR plan is created."""
    creator = getattr(instance, 'created_by', None) or instance.owner
    
    if not creator or not created:
        return
    
    is_author = user_is_author(creator)
    is_manager_user = user_is_manager(creator)
    
    if is_author and not is_manager_user:
        if instance.status in ['draft']:
            DisasterRecoveryPlan.objects.filter(pk=instance.pk).update(status='pending_approval')
            instance.refresh_from_db()
        start_content_workflow(instance, creator, 'DRPlan', 'plan_id')
    elif is_manager_user:
        DisasterRecoveryPlan.objects.filter(pk=instance.pk).update(status='approved')
        logger.info(f"Auto-approved DR plan {instance.plan_id} by manager")


@receiver(post_save, sender=BCMTest)
def trigger_bcmtest_workflow(sender, instance, created, **kwargs):
    """Trigger workflow when BCM test is created."""
    creator = getattr(instance, 'created_by', None) or instance.coordinator
    
    if not creator or not created:
        return
    
    is_author = user_is_author(creator)
    is_manager_user = user_is_manager(creator)
    
    if is_author and not is_manager_user:
        if instance.status in ['draft', 'planned']:
            BCMTest.objects.filter(pk=instance.pk).update(status='pending_approval')
            instance.refresh_from_db()
        start_content_workflow(instance, creator, 'BCMTest', 'test_id')
    elif is_manager_user:
        BCMTest.objects.filter(pk=instance.pk).update(status='planned')
        logger.info(f"Auto-approved BCM test {instance.test_id} by manager")


# Connect workflow completion to update BCM statuses
def handle_workflow_completed(sender, instance, **kwargs):
    """Update BCM content status when workflow completes."""
    
    if 'bcm.businessfunction' in instance.content_type:
        try:
            obj = BusinessFunction.objects.get(pk=instance.object_id)
            obj.status = 'active' if instance.status == 'completed' else 'draft'
            obj.save(update_fields=['status'])
            logger.info(f"Updated business function {obj.function_id} status to {obj.status}")
        except BusinessFunction.DoesNotExist:
            pass
    
    elif 'bcm.bcplan' in instance.content_type:
        try:
            obj = BCPlan.objects.get(pk=instance.object_id)
            obj.status = 'approved' if instance.status == 'completed' else 'draft'
            obj.save(update_fields=['status'])
            logger.info(f"Updated BC plan {obj.plan_id} status to {obj.status}")
        except BCPlan.DoesNotExist:
            pass
    
    elif 'bcm.disasterrecoveryplan' in instance.content_type:
        try:
            obj = DisasterRecoveryPlan.objects.get(pk=instance.object_id)
            obj.status = 'approved' if instance.status == 'completed' else 'draft'
            obj.save(update_fields=['status'])
            logger.info(f"Updated DR plan {obj.plan_id} status to {obj.status}")
        except DisasterRecoveryPlan.DoesNotExist:
            pass
    
    elif 'bcm.bcmtest' in instance.content_type:
        try:
            obj = BCMTest.objects.get(pk=instance.object_id)
            obj.status = 'planned' if instance.status == 'completed' else 'draft'
            obj.save(update_fields=['status'])
            logger.info(f"Updated BCM test {obj.test_id} status to {obj.status}")
        except BCMTest.DoesNotExist:
            pass


# Connect to workflow signals
from workflow.signals import workflow_completed
workflow_completed.connect(handle_workflow_completed)
