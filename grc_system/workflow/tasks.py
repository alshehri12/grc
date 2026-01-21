"""
Celery tasks for workflow automation.
Handles SLA monitoring, reminders, and escalations.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_overdue_approvals(self):
    """
    Check for overdue approvals and mark them accordingly.
    Runs hourly via Celery Beat.
    """
    from .models import Approval, WorkflowInstance
    from .services import WorkflowService
    
    try:
        now = timezone.now()
        
        # Find pending approvals that are past due
        overdue_approvals = Approval.objects.filter(
            status='pending',
            due_date__lt=now
        ).select_related('workflow_instance', 'step', 'assignee')
        
        escalated_count = 0
        for approval in overdue_approvals:
            try:
                # Check if escalation is needed
                if WorkflowService.check_and_escalate(approval.workflow_instance):
                    escalated_count += 1
            except Exception as e:
                logger.error(f"Error processing overdue approval {approval.pk}: {e}")
        
        logger.info(f"Checked overdue approvals: {overdue_approvals.count()} overdue, {escalated_count} escalated")
        
        return {
            'overdue_count': overdue_approvals.count(),
            'escalated_count': escalated_count
        }
        
    except Exception as e:
        logger.error(f"Error in check_overdue_approvals: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_reminder_notifications(self):
    """
    Send reminder notifications for approvals due soon.
    Runs daily via Celery Beat.
    """
    from .models import Approval
    from notifications.models import Notification, NotificationTemplate
    
    try:
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        
        # Find approvals due within 24 hours that haven't been reminded
        upcoming_approvals = Approval.objects.filter(
            status='pending',
            due_date__gte=now,
            due_date__lte=tomorrow
        ).select_related('workflow_instance', 'step', 'assignee')
        
        # Get reminder template
        template = NotificationTemplate.objects.filter(
            event_type='task_due',
            is_active=True
        ).first()
        
        reminders_sent = 0
        for approval in upcoming_approvals:
            if not approval.assignee:
                continue
            
            # Check if reminder already sent today
            existing_reminder = Notification.objects.filter(
                recipient=approval.assignee,
                content_type='workflow.approval',
                object_id=approval.pk,
                created_at__gte=now - timedelta(hours=24)
            ).exists()
            
            if existing_reminder:
                continue
            
            # Send reminder
            try:
                Notification.objects.create(
                    template=template,
                    recipient=approval.assignee,
                    subject=f"Reminder: Approval Due Tomorrow - {approval.workflow_instance.object_title}",
                    body=f"""
This is a reminder that you have a pending approval due tomorrow.

Workflow: {approval.workflow_instance.template.name}
Item: {approval.workflow_instance.object_title}
Step: {approval.step.name}
Due Date: {approval.due_date.strftime('%Y-%m-%d %H:%M')}

Please take action before the deadline to avoid escalation.
""",
                    channel='in_app',
                    priority='high',
                    content_type='workflow.approval',
                    object_id=approval.pk
                )
                reminders_sent += 1
                
                # Record in history
                from .models import WorkflowHistory
                WorkflowHistory.objects.create(
                    workflow_instance=approval.workflow_instance,
                    action='reminder_sent',
                    details=f"Reminder sent to {approval.assignee.get_full_name()}",
                    step_number=approval.step.order
                )
                
            except Exception as e:
                logger.error(f"Error sending reminder for approval {approval.pk}: {e}")
        
        logger.info(f"Sent {reminders_sent} reminder notifications")
        
        return {'reminders_sent': reminders_sent}
        
    except Exception as e:
        logger.error(f"Error in send_reminder_notifications: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_escalations(self):
    """
    Process pending escalations and notify appropriate parties.
    Runs every 4 hours via Celery Beat.
    """
    from notifications.models import Escalation, Notification
    
    try:
        # Find pending escalations
        pending_escalations = Escalation.objects.filter(
            status='pending'
        ).select_related('escalated_from', 'escalated_to')
        
        processed_count = 0
        for escalation in pending_escalations:
            try:
                # Send notification to escalated_to user
                if escalation.escalated_to:
                    Notification.objects.create(
                        recipient=escalation.escalated_to,
                        subject=f"Escalation: {escalation.object_title}",
                        body=f"""
An item has been escalated to you due to SLA breach.

Item: {escalation.object_title}
Reason: {escalation.reason}
Level: {escalation.level}
Originally assigned to: {escalation.escalated_from.get_full_name() if escalation.escalated_from else 'Unknown'}

Please review and take appropriate action.
""",
                        channel='in_app',
                        priority='urgent',
                        content_type=escalation.content_type,
                        object_id=escalation.object_id
                    )
                
                # Mark as escalated
                escalation.status = 'escalated'
                escalation.save()
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing escalation {escalation.pk}: {e}")
        
        logger.info(f"Processed {processed_count} escalations")
        
        return {'processed_count': processed_count}
        
    except Exception as e:
        logger.error(f"Error in process_escalations: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def update_overdue_task_status(self):
    """
    Update task status to 'overdue' for tasks past their due date.
    Runs hourly via Celery Beat.
    """
    from .models import Task
    
    try:
        now = timezone.now()
        
        # Find tasks that are overdue but not marked as such
        overdue_tasks = Task.objects.filter(
            status__in=['pending', 'in_progress'],
            due_date__lt=now
        ).exclude(status='overdue')
        
        updated_count = overdue_tasks.update(status='overdue')
        
        logger.info(f"Updated {updated_count} tasks to overdue status")
        
        return {'updated_count': updated_count}
        
    except Exception as e:
        logger.error(f"Error in update_overdue_task_status: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def send_workflow_notification(self, notification_type, workflow_instance_id, user_id=None, extra_data=None):
    """
    Send a workflow-related notification.
    Called by the workflow service for various events.
    
    Args:
        notification_type: Type of notification (e.g., 'approval_required', 'workflow_completed')
        workflow_instance_id: ID of the WorkflowInstance
        user_id: Optional specific user to notify
        extra_data: Optional extra context data
    """
    from .models import WorkflowInstance
    from notifications.models import Notification, NotificationTemplate
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        instance = WorkflowInstance.objects.select_related('template', 'initiated_by').get(pk=workflow_instance_id)
        
        # Determine recipient
        recipient = None
        if user_id:
            recipient = User.objects.get(pk=user_id)
        elif instance.initiated_by:
            recipient = instance.initiated_by
        
        if not recipient:
            logger.warning(f"No recipient for workflow notification: {workflow_instance_id}")
            return
        
        # Get template
        template = NotificationTemplate.objects.filter(
            event_type=notification_type,
            is_active=True
        ).first()
        
        # Build subject and body based on type
        subjects = {
            'workflow_started': f"Workflow Started: {instance.object_title}",
            'workflow_completed': f"Workflow Completed: {instance.object_title}",
            'workflow_rejected': f"Workflow Rejected: {instance.object_title}",
            'approval_required': f"Approval Required: {instance.object_title}",
        }
        
        subject = subjects.get(notification_type, f"Workflow Update: {instance.object_title}")
        body = f"""
Workflow: {instance.template.name}
Item: {instance.object_title}
Status: {instance.get_status_display()}
Current Step: {instance.current_step}

{extra_data.get('message', '') if extra_data else ''}
"""
        
        Notification.objects.create(
            template=template,
            recipient=recipient,
            subject=subject,
            body=body,
            channel='in_app',
            priority='normal',
            content_type='workflow.workflowinstance',
            object_id=instance.pk
        )
        
        logger.info(f"Sent {notification_type} notification for workflow {workflow_instance_id}")
        
    except WorkflowInstance.DoesNotExist:
        logger.error(f"WorkflowInstance not found: {workflow_instance_id}")
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
    except Exception as e:
        logger.error(f"Error sending workflow notification: {e}")
