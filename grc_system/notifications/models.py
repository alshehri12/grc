"""
Notification models for the GRC system.
Email/SMS alerts, reminders, and escalations.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class NotificationTemplate(models.Model):
    """
    قالب الإشعار - Notification template
    """
    CHANNEL_CHOICES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('in_app', _('In-App')),
        ('all', _('All Channels')),
    ]
    
    EVENT_TYPES = [
        ('task_assigned', _('Task Assigned')),
        ('task_due', _('Task Due Soon')),
        ('task_overdue', _('Task Overdue')),
        ('approval_required', _('Approval Required')),
        ('approval_completed', _('Approval Completed')),
        ('approval_rejected', _('Approval Rejected')),
        ('policy_review', _('Policy Review Due')),
        ('risk_assessment', _('Risk Assessment Due')),
        ('audit_scheduled', _('Audit Scheduled')),
        ('evidence_expiring', _('Evidence Expiring')),
        ('control_testing', _('Control Testing Due')),
        ('bcm_test', _('BCM Test Scheduled')),
        ('escalation', _('Escalation')),
        ('custom', _('Custom')),
    ]
    
    code = models.CharField(_('Template Code'), max_length=50, unique=True)
    name = models.CharField(_('Template Name'), max_length=200)
    name_ar = models.CharField(_('اسم القالب'), max_length=200, blank=True)
    event_type = models.CharField(_('Event Type'), max_length=30, choices=EVENT_TYPES)
    channel = models.CharField(_('Channel'), max_length=20, choices=CHANNEL_CHOICES, default='email')
    
    # English content
    subject = models.CharField(_('Subject'), max_length=300)
    body = models.TextField(_('Body'))
    
    # Arabic content
    subject_ar = models.CharField(_('الموضوع'), max_length=300, blank=True)
    body_ar = models.TextField(_('المحتوى'), blank=True)
    
    # Settings
    is_active = models.BooleanField(_('Active'), default=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['event_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.event_type})"


class Notification(models.Model):
    """
    الإشعار - Individual notification
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('failed', _('Failed')),
        ('read', _('Read')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='notifications',
        verbose_name=_('Template')
    )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient')
    )
    
    # Content
    subject = models.CharField(_('Subject'), max_length=300)
    body = models.TextField(_('Body'))
    
    # Metadata
    channel = models.CharField(_('Channel'), max_length=20, default='in_app')
    priority = models.CharField(_('Priority'), max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Related object
    content_type = models.CharField(_('Content Type'), max_length=100, blank=True)
    object_id = models.PositiveIntegerField(_('Object ID'), null=True, blank=True)
    
    # Tracking
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    read_at = models.DateTimeField(_('Read At'), null=True, blank=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['recipient', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.recipient}"


class Reminder(models.Model):
    """
    التذكير - Scheduled reminder
    """
    FREQUENCY_CHOICES = [
        ('once', _('Once')),
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('paused', _('Paused')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    title = models.CharField(_('Reminder Title'), max_length=300)
    title_ar = models.CharField(_('عنوان التذكير'), max_length=300, blank=True)
    message = models.TextField(_('Message'))
    message_ar = models.TextField(_('الرسالة'), blank=True)
    
    # Target
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name=_('Recipient')
    )
    
    # Related object
    content_type = models.CharField(_('Content Type'), max_length=100, blank=True)
    object_id = models.PositiveIntegerField(_('Object ID'), null=True, blank=True)
    
    # Schedule
    frequency = models.CharField(_('Frequency'), max_length=20, choices=FREQUENCY_CHOICES, default='once')
    scheduled_date = models.DateTimeField(_('Scheduled Date'))
    days_before = models.PositiveIntegerField(_('Days Before'), default=7)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Tracking
    last_sent_at = models.DateTimeField(_('Last Sent At'), null=True, blank=True)
    send_count = models.PositiveIntegerField(_('Send Count'), default=0)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_reminders',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Reminder')
        verbose_name_plural = _('Reminders')
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"{self.title} - {self.recipient}"


class Escalation(models.Model):
    """
    التصعيد - Escalation rules and records
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('escalated', _('Escalated')),
        ('resolved', _('Resolved')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Related object
    content_type = models.CharField(_('Content Type'), max_length=100)
    object_id = models.PositiveIntegerField(_('Object ID'))
    object_title = models.CharField(_('Object Title'), max_length=500)
    
    # Escalation chain
    level = models.PositiveIntegerField(_('Escalation Level'), default=1)
    escalated_from = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='escalations_from',
        verbose_name=_('Escalated From')
    )
    escalated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='escalations_to',
        verbose_name=_('Escalated To')
    )
    
    reason = models.TextField(_('Reason'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Resolution
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_escalations',
        verbose_name=_('Resolved By')
    )
    resolved_at = models.DateTimeField(_('Resolved At'), null=True, blank=True)
    resolution_notes = models.TextField(_('Resolution Notes'), blank=True)
    
    escalated_at = models.DateTimeField(_('Escalated At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Escalation')
        verbose_name_plural = _('Escalations')
        ordering = ['-escalated_at']
    
    def __str__(self):
        return f"Escalation L{self.level}: {self.object_title}"
