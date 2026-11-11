"""
Workflow Service - core workflow engine logic.
Handles workflow lifecycle: start, advance, approve, reject, delegate, cancel, escalate.

Segregation of duties (maker-checker):
  * The approver of a step must be the assigned user (or an admin).
  * Nobody may approve a workflow they initiated - not even an admin.
  * When the natural approver (department manager) *is* the initiator, the
    approval is routed one level up the department hierarchy.
"""
import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from core.audit import log_action
from core.permissions import user_is_admin
from .models import WorkflowTemplate, WorkflowInstance, Approval, Task, WorkflowHistory

logger = logging.getLogger('grc.workflow')


class WorkflowPermissionError(PermissionError):
    """Raised when a user attempts a workflow action they are not allowed to take."""


class WorkflowService:
    """Centralized service for managing workflow operations."""

    # ------------------------------------------------------------------ #
    # Starting
    # ------------------------------------------------------------------ #
    @classmethod
    def start_workflow(cls, template_code, obj, initiated_by):
        try:
            template = WorkflowTemplate.objects.get(code=template_code, is_active=True)
        except WorkflowTemplate.DoesNotExist:
            raise ValueError(f"Workflow template '{template_code}' not found or inactive")

        content_type = ContentType.objects.get_for_model(obj)
        due_date = timezone.now() + timedelta(days=template.default_sla_days)

        with transaction.atomic():
            instance = WorkflowInstance.objects.create(
                template=template,
                content_type=f"{content_type.app_label}.{content_type.model}",
                object_id=obj.pk,
                object_title=str(obj)[:500],
                status='in_progress',
                current_step=1,
                initiated_by=initiated_by,
                due_date=due_date,
            )
            first_step = template.steps.filter(order=1).first()
            if first_step:
                cls._create_approval_for_step(instance, first_step)

            cls._record_history(instance, 'workflow_started', initiated_by, f"Workflow '{template.name}' started")
            log_action(initiated_by, 'submit', obj, changes={'workflow_instance': instance.pk})

            from .signals import workflow_started
            workflow_started.send(sender=cls, instance=instance, obj=obj)
            return instance

    @classmethod
    def _create_approval_for_step(cls, instance, step):
        assignee = cls._resolve_assignee(instance, step)
        if assignee is None:
            logger.warning('No approver could be resolved for workflow %s step %s', instance.pk, step.order)

        sla_days = step.sla_days or instance.template.default_sla_days
        approval = Approval.objects.create(
            workflow_instance=instance,
            step=step,
            assignee=assignee,
            status='pending',
            due_date=timezone.now() + timedelta(days=sla_days),
        )
        cls._notify_assignee(approval)
        return approval

    # ------------------------------------------------------------------ #
    # Assignee resolution
    # ------------------------------------------------------------------ #
    @classmethod
    def _resolve_assignee(cls, instance, step):
        initiator = instance.initiated_by

        if step.assignee_type == 'user' and step.assignee_user:
            return step.assignee_user

        if step.assignee_type == 'role' and step.assignee_role:
            from core.models import UserProfile
            qs = UserProfile.objects.filter(roles=step.assignee_role, user__is_active=True)
            if initiator:
                qs = qs.exclude(user=initiator)
            profile = qs.select_related('user').first()
            return profile.user if profile else None

        if step.assignee_type == 'manager':
            return cls._resolve_manager(instance)

        if step.assignee_type == 'owner':
            obj = cls._get_workflow_object(instance)
            return getattr(obj, 'owner', None) if obj else None

        return None

    @classmethod
    def _resolve_manager(cls, instance):
        """
        Find an approver who is NOT the initiator, walking up the department tree:
        initiator's department manager -> parent department manager -> ... ->
        object's department manager -> any other manager in the org -> any admin.
        """
        from core.models import UserProfile
        initiator = instance.initiated_by
        initiator_id = initiator.pk if initiator else None

        def ok(user):
            return user is not None and user.is_active and user.pk != initiator_id

        start_departments = []
        profile = None
        if initiator:
            profile = UserProfile.objects.filter(user=initiator).select_related('department', 'organization').first()
            if profile and profile.department:
                start_departments.append(profile.department)

        obj = cls._get_workflow_object(instance)
        obj_department = getattr(obj, 'department', None) if obj else None
        if obj_department:
            start_departments.append(obj_department)
        owner = getattr(obj, 'owner', None) if obj else None
        if owner:
            owner_profile = UserProfile.objects.filter(user=owner).select_related('department').first()
            if owner_profile and owner_profile.department:
                start_departments.append(owner_profile.department)

        # Walk up each candidate department chain.
        for dept in start_departments:
            current, hops = dept, 0
            while current is not None and hops < 10:
                if ok(current.manager):
                    return current.manager
                current, hops = current.parent, hops + 1

        # Fallback: another manager in the same organization, then any admin.
        organization = (profile.organization if profile else None) or getattr(obj, 'organization', None)
        managers = UserProfile.objects.filter(roles__code='manager', user__is_active=True)
        if organization:
            managers = managers.filter(organization=organization)
        if initiator_id:
            managers = managers.exclude(user_id=initiator_id)
        candidate = managers.select_related('user').order_by('user_id').first()
        if candidate:
            return candidate.user

        admins = UserProfile.objects.filter(roles__code='admin', user__is_active=True)
        if initiator_id:
            admins = admins.exclude(user_id=initiator_id)
        candidate = admins.select_related('user').order_by('user_id').first()
        if candidate:
            return candidate.user

        from django.contrib.auth import get_user_model
        return get_user_model().objects.filter(is_superuser=True, is_active=True).exclude(pk=initiator_id).first()

    @classmethod
    def _get_workflow_object(cls, instance):
        try:
            app_label, model_name = instance.content_type.split('.')
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
            return ct.get_object_for_this_type(pk=instance.object_id)
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Notifications
    # ------------------------------------------------------------------ #
    @classmethod
    def _notify_assignee(cls, approval):
        if not approval.assignee:
            return
        try:
            from notifications.models import Notification, NotificationTemplate
            template = NotificationTemplate.objects.filter(event_type='approval_required', is_active=True).first()
            wf = approval.workflow_instance
            body = (
                f"You have a pending approval request.\n\n"
                f"Workflow: {wf.template.name}\nItem: {wf.object_title}\nStep: {approval.step.name}\n"
                f"Submitted by: {wf.initiated_by.get_full_name() if wf.initiated_by else 'N/A'}\n"
                f"Due Date: {approval.due_date.strftime('%Y-%m-%d %H:%M') if approval.due_date else 'N/A'}\n\n"
                f"{approval.step.instructions or 'Please review and take action.'}"
            )
            Notification.objects.create(
                template=template, recipient=approval.assignee,
                subject=f"Approval Required: {wf.object_title}"[:300], body=body,
                channel='in_app', priority='normal',
                content_type='workflow.approval', object_id=approval.pk,
            )
        except Exception:
            logger.exception('Failed to create approval notification')

    # ------------------------------------------------------------------ #
    # Authority checks
    # ------------------------------------------------------------------ #
    @classmethod
    def can_decide(cls, user, approval):
        """True if `user` may approve/reject this approval."""
        if not user or not user.is_authenticated or approval.status != 'pending':
            return False
        initiator_id = approval.workflow_instance.initiated_by_id
        if initiator_id and initiator_id == user.pk:
            return False  # never approve your own submission
        if approval.assignee_id == user.pk:
            return True
        return user_is_admin(user)

    @classmethod
    def assert_can_decide(cls, user, approval):
        if approval.status != 'pending':
            raise ValueError('Approval has already been processed')
        if approval.workflow_instance.initiated_by_id == user.pk:
            raise WorkflowPermissionError('You cannot approve or reject your own submission')
        if not cls.can_decide(user, approval):
            raise WorkflowPermissionError('Only the assigned approver (or an administrator) can decide this approval')

    # ------------------------------------------------------------------ #
    # Decisions
    # ------------------------------------------------------------------ #
    @classmethod
    def handle_approval_decision(cls, approval, decision, user, comments='', request=None):
        """
        Approve or reject. Returns (approval, workflow_finished).
        Raises ValueError (already processed) or WorkflowPermissionError.
        """
        if decision not in ('approved', 'rejected'):
            raise ValueError('decision must be "approved" or "rejected"')
        cls.assert_can_decide(user, approval)
        if decision == 'rejected' and not (comments or '').strip():
            raise ValueError('A reason is required when rejecting')

        with transaction.atomic():
            approval.status = decision
            approval.decided_by = user
            approval.decided_at = timezone.now()
            approval.comments = comments
            approval.save()

            wf = approval.workflow_instance
            cls._record_history(wf, 'approval_decision', user, f"Step '{approval.step.name}' {decision}: {comments}")
            log_action(user, 'approve' if decision == 'approved' else 'reject',
                       content_type=wf.content_type, object_id=wf.object_id, object_repr=wf.object_title,
                       changes={'workflow_instance': wf.pk, 'step': approval.step.order, 'comments': comments},
                       request=request)

            from .signals import step_completed
            step_completed.send(sender=cls, instance=wf, step=approval.step, approval=approval, decision=decision)

            if decision == 'approved':
                return cls._advance_workflow(wf)
            return cls._reject_workflow(wf, comments)

    @classmethod
    def _advance_workflow(cls, instance):
        next_step = instance.template.steps.filter(order=instance.current_step + 1).first()
        if next_step:
            instance.current_step = next_step.order
            instance.save(update_fields=['current_step'])
            cls._create_approval_for_step(instance, next_step)
            return instance, False
        return cls._complete_workflow(instance)

    @classmethod
    def _complete_workflow(cls, instance):
        instance.status = 'completed'
        instance.completed_at = timezone.now()
        instance.save(update_fields=['status', 'completed_at'])
        cls._record_history(instance, 'workflow_completed', None, 'Workflow completed successfully')
        from .signals import workflow_completed
        workflow_completed.send(sender=cls, instance=instance)
        cls._notify_initiator(instance, 'approved')
        return instance, True

    @classmethod
    def _reject_workflow(cls, instance, reason=''):
        instance.status = 'rejected'
        instance.completed_at = timezone.now()
        instance.notes = reason
        instance.save(update_fields=['status', 'completed_at', 'notes'])
        cls._record_history(instance, 'workflow_rejected', None, f'Workflow rejected: {reason}')
        from .signals import workflow_completed
        workflow_completed.send(sender=cls, instance=instance)
        cls._notify_initiator(instance, 'rejected', reason)
        return instance, True

    @classmethod
    def _notify_initiator(cls, instance, outcome, reason=''):
        if not instance.initiated_by:
            return
        try:
            from notifications.models import Notification
            Notification.objects.create(
                recipient=instance.initiated_by,
                subject=f"{outcome.title()}: {instance.object_title}"[:300],
                body=(f"Your submission '{instance.object_title}' was {outcome}."
                      + (f"\n\nReason: {reason}" if reason else '')),
                channel='in_app', priority='normal' if outcome == 'approved' else 'high',
                content_type=instance.content_type, object_id=instance.object_id,
            )
        except Exception:
            logger.exception('Failed to notify initiator')

    # ------------------------------------------------------------------ #
    # Cancel / delegate / escalate
    # ------------------------------------------------------------------ #
    @classmethod
    def cancel_workflow(cls, instance, user, reason='', request=None):
        if instance.status in ('completed', 'rejected', 'cancelled'):
            raise ValueError('Workflow is already finished')
        if not (user_is_admin(user) or instance.initiated_by_id == user.pk):
            raise WorkflowPermissionError('Only the initiator or an administrator can cancel this workflow')

        with transaction.atomic():
            instance.status = 'cancelled'
            instance.completed_at = timezone.now()
            instance.notes = reason
            instance.save(update_fields=['status', 'completed_at', 'notes'])
            instance.approvals.filter(status='pending').update(status='delegated', decided_at=timezone.now())
            cls._record_history(instance, 'workflow_cancelled', user, f'Cancelled: {reason}')
            log_action(user, 'update', content_type=instance.content_type, object_id=instance.object_id,
                       object_repr=instance.object_title,
                       changes={'workflow_instance': instance.pk, 'workflow_status': ['in_progress', 'cancelled'],
                                'reason': reason}, request=request)
            from .signals import workflow_completed
            workflow_completed.send(sender=cls, instance=instance)
        return instance

    @classmethod
    def delegate_approval(cls, approval, from_user, to_user, reason='', request=None):
        if approval.status != 'pending':
            raise ValueError('Can only delegate pending approvals')
        if not approval.step.allow_delegation:
            raise ValueError('This step does not allow delegation')
        if not (approval.assignee_id == from_user.pk or user_is_admin(from_user)):
            raise WorkflowPermissionError('Only the assigned approver (or an administrator) can delegate')
        if to_user.pk == approval.workflow_instance.initiated_by_id:
            raise WorkflowPermissionError('Cannot delegate an approval to the person who submitted it')
        if to_user.pk == approval.assignee_id:
            raise ValueError('Approval is already assigned to this user')

        with transaction.atomic():
            approval.delegated_to = to_user
            approval.delegated_at = timezone.now()
            approval.assignee = to_user
            approval.save()
            cls._record_history(approval.workflow_instance, 'approval_delegated', from_user,
                                f'Delegated to {to_user.get_full_name() or to_user.username}: {reason}')
            log_action(from_user, 'update', content_type='workflow.approval', object_id=approval.pk,
                       object_repr=str(approval), changes={'delegated_to': to_user.pk, 'reason': reason},
                       request=request)
            cls._notify_assignee(approval)
            from .signals import approval_delegated
            approval_delegated.send(sender=cls, approval=approval, from_user=from_user, to_user=to_user)

    @classmethod
    def check_and_escalate(cls, instance):
        """Escalate an overdue pending approval to the assignee's manager. Returns True if escalated."""
        if not instance.template.escalation_enabled:
            return False
        pending = instance.approvals.filter(status='pending').first()
        if not pending or not pending.due_date or timezone.now() <= pending.due_date:
            return False

        from notifications.models import Escalation
        if Escalation.objects.filter(content_type='workflow.approval', object_id=pending.pk, status='pending').exists():
            return False

        escalated_to = None
        if pending.assignee:
            from core.models import UserProfile
            profile = UserProfile.objects.filter(user=pending.assignee).select_related('department').first()
            dept = profile.department if profile else None
            while dept is not None and escalated_to is None:
                if dept.manager and dept.manager.pk not in (pending.assignee_id, instance.initiated_by_id):
                    escalated_to = dept.manager
                dept = dept.parent

        Escalation.objects.create(
            content_type='workflow.approval', object_id=pending.pk, object_title=instance.object_title,
            level=1, escalated_from=pending.assignee, escalated_to=escalated_to,
            reason=f'SLA breached for approval step: {pending.step.name}', status='pending',
        )
        from .signals import workflow_escalated
        workflow_escalated.send(sender=cls, instance=instance, approval=pending)
        cls._record_history(instance, 'escalation', None, 'Escalated due to SLA breach')
        return True

    # ------------------------------------------------------------------ #
    # Helpers / queries
    # ------------------------------------------------------------------ #
    @classmethod
    def _record_history(cls, instance, action, user, details):
        try:
            WorkflowHistory.objects.create(
                workflow_instance=instance, action=action, performed_by=user,
                details=details, step_number=instance.current_step,
            )
        except Exception:
            logger.exception('Failed to record workflow history')

    @classmethod
    def get_pending_approvals_for_user(cls, user):
        return Approval.objects.filter(assignee=user, status='pending').select_related(
            'workflow_instance', 'workflow_instance__template', 'step').order_by('due_date')

    @classmethod
    def get_user_tasks(cls, user, include_completed=False):
        qs = Task.objects.filter(assigned_to=user)
        if not include_completed:
            qs = qs.exclude(status='completed')
        return qs.select_related('assigned_by').order_by('-priority', 'due_date')

    @classmethod
    def get_workflow_for_object(cls, obj):
        content_type = ContentType.objects.get_for_model(obj)
        return WorkflowInstance.objects.filter(
            content_type=f"{content_type.app_label}.{content_type.model}",
            object_id=obj.pk, status__in=['pending', 'in_progress'],
        ).first()
