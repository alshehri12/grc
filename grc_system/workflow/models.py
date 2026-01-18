"""
Workflow models for the GRC system.
Approval workflows, task assignments, and status tracking.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class WorkflowTemplate(models.Model):
    """
    قالب سير العمل - Workflow template definition
    """
    WORKFLOW_TYPES = [
        ('approval', _('Approval Workflow')),
        ('review', _('Review Workflow')),
        ('sequential', _('Sequential Workflow')),
        ('parallel', _('Parallel Workflow')),
    ]
    
    name = models.CharField(_('Workflow Name'), max_length=200)
    name_ar = models.CharField(_('اسم سير العمل'), max_length=200, blank=True)
    code = models.CharField(_('Workflow Code'), max_length=50, unique=True)
    workflow_type = models.CharField(_('Workflow Type'), max_length=20, choices=WORKFLOW_TYPES, default='approval')
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Applicable to which model types
    applicable_models = models.JSONField(
        _('Applicable Models'), 
        default=list,
        help_text=_('List of model types this workflow applies to')
    )
    
    # SLA settings
    default_sla_days = models.PositiveIntegerField(_('Default SLA (Days)'), default=5)
    escalation_enabled = models.BooleanField(_('Escalation Enabled'), default=True)
    escalation_days = models.PositiveIntegerField(_('Escalation After (Days)'), default=3)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_workflow_templates',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Workflow Template')
        verbose_name_plural = _('Workflow Templates')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class WorkflowStep(models.Model):
    """
    خطوة سير العمل - Individual step in a workflow
    """
    STEP_TYPES = [
        ('approval', _('Approval')),
        ('review', _('Review')),
        ('notification', _('Notification')),
        ('task', _('Task')),
    ]
    
    ASSIGNEE_TYPES = [
        ('user', _('Specific User')),
        ('role', _('Role')),
        ('manager', _('Department Manager')),
        ('owner', _('Object Owner')),
    ]
    
    template = models.ForeignKey(
        WorkflowTemplate, 
        on_delete=models.CASCADE, 
        related_name='steps',
        verbose_name=_('Workflow Template')
    )
    order = models.PositiveIntegerField(_('Step Order'))
    name = models.CharField(_('Step Name'), max_length=200)
    name_ar = models.CharField(_('اسم الخطوة'), max_length=200, blank=True)
    step_type = models.CharField(_('Step Type'), max_length=20, choices=STEP_TYPES, default='approval')
    
    # Assignee configuration
    assignee_type = models.CharField(_('Assignee Type'), max_length=20, choices=ASSIGNEE_TYPES, default='role')
    assignee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_workflow_steps',
        verbose_name=_('Assignee User')
    )
    assignee_role = models.ForeignKey(
        'core.Role', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='workflow_steps',
        verbose_name=_('Assignee Role')
    )
    
    # Step settings
    sla_days = models.PositiveIntegerField(_('SLA (Days)'), null=True, blank=True)
    is_required = models.BooleanField(_('Required'), default=True)
    allow_delegation = models.BooleanField(_('Allow Delegation'), default=True)
    
    instructions = models.TextField(_('Instructions'), blank=True)
    instructions_ar = models.TextField(_('التعليمات'), blank=True)
    
    class Meta:
        verbose_name = _('Workflow Step')
        verbose_name_plural = _('Workflow Steps')
        ordering = ['template', 'order']
        unique_together = ['template', 'order']
    
    def __str__(self):
        return f"{self.template.name} - Step {self.order}: {self.name}"


class WorkflowInstance(models.Model):
    """
    مثيل سير العمل - Active workflow instance
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    ]
    
    template = models.ForeignKey(
        WorkflowTemplate, 
        on_delete=models.PROTECT,
        related_name='instances',
        verbose_name=_('Workflow Template')
    )
    
    # Generic relation to the object being processed
    content_type = models.CharField(_('Content Type'), max_length=100)
    object_id = models.PositiveIntegerField(_('Object ID'))
    object_title = models.CharField(_('Object Title'), max_length=500, blank=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    current_step = models.PositiveIntegerField(_('Current Step'), default=1)
    
    # Tracking
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='initiated_workflows',
        verbose_name=_('Initiated By')
    )
    started_at = models.DateTimeField(_('Started At'), auto_now_add=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    due_date = models.DateTimeField(_('Due Date'), null=True, blank=True)
    
    # Comments/notes
    notes = models.TextField(_('Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Workflow Instance')
        verbose_name_plural = _('Workflow Instances')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"{self.template.name} - {self.object_title}"
    
    @property
    def is_overdue(self):
        if self.due_date and self.status in ['pending', 'in_progress']:
            return timezone.now() > self.due_date
        return False


class Approval(models.Model):
    """
    الاعتماد - Individual approval record
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('delegated', _('Delegated')),
    ]
    
    workflow_instance = models.ForeignKey(
        WorkflowInstance, 
        on_delete=models.CASCADE,
        related_name='approvals',
        verbose_name=_('Workflow Instance')
    )
    step = models.ForeignKey(
        WorkflowStep, 
        on_delete=models.PROTECT,
        related_name='approvals',
        verbose_name=_('Workflow Step')
    )
    
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='assigned_approvals',
        verbose_name=_('Assignee')
    )
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Decision tracking
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='decided_approvals',
        verbose_name=_('Decided By')
    )
    decided_at = models.DateTimeField(_('Decided At'), null=True, blank=True)
    comments = models.TextField(_('Comments'), blank=True)
    
    # Delegation
    delegated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='delegated_approvals',
        verbose_name=_('Delegated To')
    )
    delegated_at = models.DateTimeField(_('Delegated At'), null=True, blank=True)
    
    # Tracking
    due_date = models.DateTimeField(_('Due Date'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Approval')
        verbose_name_plural = _('Approvals')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.workflow_instance} - {self.step.name} - {self.status}"


class Task(models.Model):
    """
    المهمة - Task assignment and tracking
    """
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('overdue', _('Overdue')),
    ]
    
    TASK_TYPES = [
        ('general', _('General Task')),
        ('review', _('Review Task')),
        ('assessment', _('Assessment Task')),
        ('evidence', _('Evidence Collection')),
        ('audit', _('Audit Task')),
        ('remediation', _('Remediation Task')),
    ]
    
    title = models.CharField(_('Task Title'), max_length=300)
    title_ar = models.CharField(_('عنوان المهمة'), max_length=300, blank=True)
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    task_type = models.CharField(_('Task Type'), max_length=20, choices=TASK_TYPES, default='general')
    priority = models.CharField(_('Priority'), max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='assigned_tasks',
        verbose_name=_('Assigned To')
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_tasks',
        verbose_name=_('Assigned By')
    )
    
    # Related object (generic relation)
    content_type = models.CharField(_('Content Type'), max_length=100, blank=True)
    object_id = models.PositiveIntegerField(_('Object ID'), null=True, blank=True)
    
    # Workflow relation
    workflow_instance = models.ForeignKey(
        WorkflowInstance, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tasks',
        verbose_name=_('Workflow Instance')
    )
    
    # Dates
    due_date = models.DateTimeField(_('Due Date'), null=True, blank=True)
    started_at = models.DateTimeField(_('Started At'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    
    # Result
    completion_notes = models.TextField(_('Completion Notes'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')
        ordering = ['-priority', 'due_date', '-created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_overdue(self):
        if self.due_date and self.status in ['pending', 'in_progress']:
            return timezone.now() > self.due_date
        return False
