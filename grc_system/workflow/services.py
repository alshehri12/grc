"""
Workflow Service - Core workflow engine logic.
Handles workflow lifecycle: start, advance, approve, reject, escalate.
"""
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from datetime import timedelta

from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, Approval, Task


class WorkflowService:
    """
    Centralized service for managing workflow operations.
    Provides a clean API for starting workflows, handling approvals,
    and managing the workflow lifecycle.
    """
    
    @classmethod
    def start_workflow(cls, template_code, obj, initiated_by):
        """
        Start a new workflow instance for an object.
        
        Args:
            template_code: The code of the workflow template to use
            obj: The Django model instance to attach the workflow to
            initiated_by: The user who initiated the workflow
            
        Returns:
            WorkflowInstance: The created workflow instance
            
        Raises:
            ValueError: If template not found or inactive
        """
        try:
            template = WorkflowTemplate.objects.get(code=template_code, is_active=True)
        except WorkflowTemplate.DoesNotExist:
            raise ValueError(f"Workflow template '{template_code}' not found or inactive")
        
        # Get content type for the object
        content_type = ContentType.objects.get_for_model(obj)
        
        # Calculate due date based on template SLA
        due_date = timezone.now() + timedelta(days=template.default_sla_days)
        
        with transaction.atomic():
            # Create workflow instance
            instance = WorkflowInstance.objects.create(
                template=template,
                content_type=f"{content_type.app_label}.{content_type.model}",
                object_id=obj.pk,
                object_title=str(obj)[:500],
                status='in_progress',
                current_step=1,
                initiated_by=initiated_by,
                due_date=due_date
            )
            
            # Create approval for first step
            first_step = template.steps.filter(order=1).first()
            if first_step:
                cls._create_approval_for_step(instance, first_step)
            
            # Import here to avoid circular imports
            from .signals import workflow_started
            workflow_started.send(sender=cls, instance=instance, obj=obj)
            
            return instance
    
    @classmethod
    def _create_approval_for_step(cls, instance, step):
        """
        Create an approval record for a workflow step.
        
        Args:
            instance: The WorkflowInstance
            step: The WorkflowStep to create approval for
            
        Returns:
            Approval: The created approval record
        """
        # Determine assignee based on step configuration
        assignee = cls._resolve_assignee(instance, step)
        
        # Calculate due date for this step
        sla_days = step.sla_days or instance.template.default_sla_days
        due_date = timezone.now() + timedelta(days=sla_days)
        
        approval = Approval.objects.create(
            workflow_instance=instance,
            step=step,
            assignee=assignee,
            status='pending',
            due_date=due_date
        )
        
        # Create notification for the assignee
        cls._notify_assignee(approval)
        
        return approval
    
    @classmethod
    def _resolve_assignee(cls, instance, step):
        """
        Resolve the assignee for a workflow step based on configuration.
        
        Args:
            instance: The WorkflowInstance
            step: The WorkflowStep
            
        Returns:
            User: The resolved assignee or None
        """
        if step.assignee_type == 'user' and step.assignee_user:
            return step.assignee_user
        
        elif step.assignee_type == 'role' and step.assignee_role:
            # Get first user with this role (can be enhanced for round-robin)
            from core.models import UserProfile
            profile = UserProfile.objects.filter(roles=step.assignee_role).first()
            return profile.user if profile else None
        
        elif step.assignee_type == 'manager':
            # First, try to get manager from the creator's department
            if instance.initiated_by:
                try:
                    from core.models import UserProfile
                    creator_profile = UserProfile.objects.get(user=instance.initiated_by)
                    if creator_profile.department and creator_profile.department.manager:
                        return creator_profile.department.manager
                except Exception:
                    pass
            
            # Fallback: Get the object and find department manager
            obj = cls._get_workflow_object(instance)
            if obj and hasattr(obj, 'department') and obj.department:
                return obj.department.manager
            
            # Fallback 2: Check if object has owner with department
            if obj and hasattr(obj, 'owner') and obj.owner:
                try:
                    from core.models import UserProfile
                    owner_profile = UserProfile.objects.get(user=obj.owner)
                    if owner_profile.department and owner_profile.department.manager:
                        return owner_profile.department.manager
                except Exception:
                    pass
            
            return None
        
        elif step.assignee_type == 'owner':
            # Get the object owner
            obj = cls._get_workflow_object(instance)
            if obj and hasattr(obj, 'owner'):
                return obj.owner
            return None
        
        return None
    
    @classmethod
    def _get_workflow_object(cls, instance):
        """
        Get the actual object attached to a workflow instance.
        
        Args:
            instance: The WorkflowInstance
            
        Returns:
            The model instance or None
        """
        try:
            app_label, model_name = instance.content_type.split('.')
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
            return ct.get_object_for_this_type(pk=instance.object_id)
        except Exception:
            return None
    
    @classmethod
    def _notify_assignee(cls, approval):
        """
        Send notification to the approval assignee.
        
        Args:
            approval: The Approval record
        """
        if not approval.assignee:
            return
        
        try:
            from notifications.models import Notification, NotificationTemplate
            
            # Try to get template
            template = NotificationTemplate.objects.filter(
                event_type='approval_required',
                is_active=True
            ).first()
            
            subject = f"Approval Required: {approval.workflow_instance.object_title}"
            body = f"""
You have a pending approval request.

Workflow: {approval.workflow_instance.template.name}
Item: {approval.workflow_instance.object_title}
Step: {approval.step.name}
Due Date: {approval.due_date.strftime('%Y-%m-%d %H:%M') if approval.due_date else 'N/A'}

{approval.step.instructions or 'Please review and take action.'}
"""
            
            Notification.objects.create(
                template=template,
                recipient=approval.assignee,
                subject=subject,
                body=body,
                channel='in_app',
                priority='normal',
                content_type=f"workflow.approval",
                object_id=approval.pk
            )
        except Exception:
            # Don't fail workflow if notification fails
            pass
    
    @classmethod
    def handle_approval_decision(cls, approval, decision, user, comments=''):
        """
        Handle an approval decision (approve or reject).
        
        Args:
            approval: The Approval record
            decision: 'approved' or 'rejected'
            user: The user making the decision
            comments: Optional comments
            
        Returns:
            tuple: (approval, workflow_completed)
        """
        if approval.status != 'pending':
            raise ValueError("Approval has already been processed")
        
        with transaction.atomic():
            # Update approval
            approval.status = decision
            approval.decided_by = user
            approval.decided_at = timezone.now()
            approval.comments = comments
            approval.save()
            
            # Record history
            cls._record_history(
                approval.workflow_instance,
                'approval_decision',
                user,
                f"Step '{approval.step.name}' {decision}: {comments}"
            )
            
            # Import signals
            from .signals import step_completed
            step_completed.send(
                sender=cls,
                instance=approval.workflow_instance,
                step=approval.step,
                approval=approval,
                decision=decision
            )
            
            if decision == 'approved':
                return cls._advance_workflow(approval.workflow_instance)
            else:
                return cls._reject_workflow(approval.workflow_instance, comments)
    
    @classmethod
    def _advance_workflow(cls, instance):
        """
        Advance workflow to the next step after approval.
        
        Args:
            instance: The WorkflowInstance
            
        Returns:
            tuple: (instance, workflow_completed)
        """
        current_step_num = instance.current_step
        next_step = instance.template.steps.filter(order=current_step_num + 1).first()
        
        if next_step:
            # Move to next step
            instance.current_step = next_step.order
            instance.save()
            
            # Create approval for next step
            cls._create_approval_for_step(instance, next_step)
            
            return instance, False
        else:
            # Workflow completed
            return cls._complete_workflow(instance)
    
    @classmethod
    def _complete_workflow(cls, instance):
        """
        Mark workflow as completed.
        
        Args:
            instance: The WorkflowInstance
            
        Returns:
            tuple: (instance, True)
        """
        instance.status = 'completed'
        instance.completed_at = timezone.now()
        instance.save()
        
        # Update the linked object status if applicable
        obj = cls._get_workflow_object(instance)
        if obj and hasattr(obj, 'status'):
            # For policies, set to approved
            if 'policy' in instance.content_type:
                obj.status = 'approved'
                obj.save()
        
        # Send completion signal
        from .signals import workflow_completed
        workflow_completed.send(sender=cls, instance=instance)
        
        cls._record_history(instance, 'workflow_completed', None, "Workflow completed successfully")
        
        return instance, True
    
    @classmethod
    def _reject_workflow(cls, instance, reason=''):
        """
        Mark workflow as rejected.
        
        Args:
            instance: The WorkflowInstance
            reason: Rejection reason
            
        Returns:
            tuple: (instance, True)
        """
        instance.status = 'rejected'
        instance.completed_at = timezone.now()
        instance.notes = reason
        instance.save()
        
        # Update linked object if applicable
        obj = cls._get_workflow_object(instance)
        if obj and hasattr(obj, 'status'):
            obj.status = 'draft'  # Return to draft
            obj.save()
        
        from .signals import workflow_completed
        workflow_completed.send(sender=cls, instance=instance)
        
        cls._record_history(instance, 'workflow_rejected', None, f"Workflow rejected: {reason}")
        
        return instance, True
    
    @classmethod
    def cancel_workflow(cls, instance, user, reason=''):
        """
        Cancel an active workflow.
        
        Args:
            instance: The WorkflowInstance
            user: User cancelling the workflow
            reason: Cancellation reason
        """
        if instance.status in ['completed', 'rejected', 'cancelled']:
            raise ValueError("Workflow is already finished")
        
        with transaction.atomic():
            instance.status = 'cancelled'
            instance.completed_at = timezone.now()
            instance.notes = reason
            instance.save()
            
            # Cancel all pending approvals
            instance.approvals.filter(status='pending').update(
                status='delegated',  # Using delegated as cancelled equivalent
                decided_at=timezone.now()
            )
            
            cls._record_history(instance, 'workflow_cancelled', user, f"Cancelled: {reason}")
    
    @classmethod
    def delegate_approval(cls, approval, from_user, to_user, reason=''):
        """
        Delegate an approval to another user.
        
        Args:
            approval: The Approval to delegate
            from_user: Current assignee
            to_user: New assignee
            reason: Reason for delegation
        """
        if approval.status != 'pending':
            raise ValueError("Can only delegate pending approvals")
        
        if not approval.step.allow_delegation:
            raise ValueError("This step does not allow delegation")
        
        with transaction.atomic():
            approval.delegated_to = to_user
            approval.delegated_at = timezone.now()
            approval.assignee = to_user
            approval.save()
            
            cls._record_history(
                approval.workflow_instance,
                'approval_delegated',
                from_user,
                f"Delegated to {to_user.get_full_name()}: {reason}"
            )
            
            # Notify new assignee
            cls._notify_assignee(approval)
    
    @classmethod
    def check_and_escalate(cls, instance):
        """
        Check if workflow/approval is overdue and escalate if needed.
        
        Args:
            instance: The WorkflowInstance
            
        Returns:
            bool: True if escalated
        """
        if not instance.template.escalation_enabled:
            return False
        
        pending_approval = instance.approvals.filter(status='pending').first()
        if not pending_approval or not pending_approval.due_date:
            return False
        
        # Check if overdue
        if timezone.now() <= pending_approval.due_date:
            return False
        
        # Already escalated recently?
        from notifications.models import Escalation
        recent_escalation = Escalation.objects.filter(
            content_type='workflow.approval',
            object_id=pending_approval.pk,
            status='pending'
        ).exists()
        
        if recent_escalation:
            return False
        
        # Create escalation
        escalated_to = None
        if pending_approval.assignee:
            # Try to find manager
            try:
                from core.models import UserProfile
                profile = UserProfile.objects.get(user=pending_approval.assignee)
                if profile.department and profile.department.manager:
                    escalated_to = profile.department.manager
            except Exception:
                pass
        
        Escalation.objects.create(
            content_type='workflow.approval',
            object_id=pending_approval.pk,
            object_title=instance.object_title,
            level=1,
            escalated_from=pending_approval.assignee,
            escalated_to=escalated_to,
            reason=f"SLA breached for approval step: {pending_approval.step.name}",
            status='pending'
        )
        
        # Send signals
        from .signals import workflow_escalated
        workflow_escalated.send(sender=cls, instance=instance, approval=pending_approval)
        
        cls._record_history(instance, 'escalation', None, f"Escalated due to SLA breach")
        
        return True
    
    @classmethod
    def _record_history(cls, instance, action, user, details):
        """
        Record an action in workflow history.
        
        Args:
            instance: The WorkflowInstance
            action: Action type string
            user: User performing action (can be None)
            details: Action details
        """
        try:
            from .models import WorkflowHistory
            WorkflowHistory.objects.create(
                workflow_instance=instance,
                action=action,
                performed_by=user,
                details=details,
                step_number=instance.current_step
            )
        except Exception:
            # Don't fail if history recording fails
            pass
    
    @classmethod
    def get_pending_approvals_for_user(cls, user):
        """
        Get all pending approvals for a user.
        
        Args:
            user: The User
            
        Returns:
            QuerySet: Pending approvals
        """
        return Approval.objects.filter(
            assignee=user,
            status='pending'
        ).select_related(
            'workflow_instance',
            'workflow_instance__template',
            'step'
        ).order_by('due_date')
    
    @classmethod
    def get_user_tasks(cls, user, include_completed=False):
        """
        Get all tasks for a user.
        
        Args:
            user: The User
            include_completed: Whether to include completed tasks
            
        Returns:
            QuerySet: User's tasks
        """
        qs = Task.objects.filter(assigned_to=user)
        if not include_completed:
            qs = qs.exclude(status='completed')
        return qs.select_related('assigned_by').order_by('-priority', 'due_date')
    
    @classmethod
    def get_workflow_for_object(cls, obj):
        """
        Get active workflow instance for an object.
        
        Args:
            obj: The model instance
            
        Returns:
            WorkflowInstance or None
        """
        content_type = ContentType.objects.get_for_model(obj)
        return WorkflowInstance.objects.filter(
            content_type=f"{content_type.app_label}.{content_type.model}",
            object_id=obj.pk,
            status__in=['pending', 'in_progress']
        ).first()
