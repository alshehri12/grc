"""
Core models for the GRC system.
Organization structure, user profiles, roles, and departments.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
    """
    المنظمة - Organization entity
    """
    name = models.CharField(_('Organization Name'), max_length=255)
    name_ar = models.CharField(_('اسم المنظمة'), max_length=255, blank=True)
    code = models.CharField(_('Organization Code'), max_length=50, unique=True)
    logo = models.ImageField(_('Logo'), upload_to='organizations/logos/', blank=True, null=True)
    
    # Contact Information
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    address = models.TextField(_('Address'), blank=True)
    address_ar = models.TextField(_('العنوان'), blank=True)
    
    # Regulatory Information
    commercial_registration = models.CharField(_('Commercial Registration'), max_length=50, blank=True)
    tax_number = models.CharField(_('Tax Number'), max_length=50, blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Department(models.Model):
    """
    الإدارة / القسم - Department within an organization
    """
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='departments',
        verbose_name=_('Organization')
    )
    name = models.CharField(_('Department Name'), max_length=255)
    name_ar = models.CharField(_('اسم الإدارة'), max_length=255, blank=True)
    code = models.CharField(_('Department Code'), max_length=50)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='children',
        verbose_name=_('Parent Department')
    )
    
    # Department head
    manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_departments',
        verbose_name=_('Department Manager')
    )
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['organization', 'name']
        unique_together = ['organization', 'code']
    
    def __str__(self):
        return f"{self.organization.code} - {self.name}"


class Role(models.Model):
    """
    الدور - System roles for RBAC
    """
    ROLE_TYPES = [
        ('system', _('System Role')),
        ('grc', _('GRC Role')),
        ('custom', _('Custom Role')),
    ]
    
    name = models.CharField(_('Role Name'), max_length=100, unique=True)
    name_ar = models.CharField(_('اسم الدور'), max_length=100, blank=True)
    code = models.CharField(_('Role Code'), max_length=50, unique=True)
    role_type = models.CharField(_('Role Type'), max_length=20, choices=ROLE_TYPES, default='custom')
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Permissions as JSON
    permissions = models.JSONField(_('Permissions'), default=dict, blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    الملف الشخصي - Extended user profile
    """
    LANGUAGE_CHOICES = [
        ('en', _('English')),
        ('ar', _('العربية')),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name=_('User')
    )
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name=_('Organization')
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name=_('Department')
    )
    
    # Arabic name fields
    first_name_ar = models.CharField(_('الاسم الأول'), max_length=100, blank=True)
    last_name_ar = models.CharField(_('اسم العائلة'), max_length=100, blank=True)
    
    # Contact
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    mobile = models.CharField(_('Mobile'), max_length=20, blank=True)
    
    # Job information
    job_title = models.CharField(_('Job Title'), max_length=200, blank=True)
    job_title_ar = models.CharField(_('المسمى الوظيفي'), max_length=200, blank=True)
    employee_id = models.CharField(_('Employee ID'), max_length=50, blank=True)
    
    # Avatar
    avatar = models.ImageField(_('Avatar'), upload_to='users/avatars/', blank=True, null=True)
    
    # Preferences
    preferred_language = models.CharField(
        _('Preferred Language'), 
        max_length=5, 
        choices=LANGUAGE_CHOICES, 
        default='en'
    )
    timezone = models.CharField(_('Timezone'), max_length=50, default='Asia/Riyadh')
    
    # Roles
    roles = models.ManyToManyField(
        Role, 
        blank=True, 
        related_name='users',
        verbose_name=_('Roles')
    )
    
    # Notifications preferences
    email_notifications = models.BooleanField(_('Email Notifications'), default=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def full_name_ar(self):
        if self.first_name_ar or self.last_name_ar:
            return f"{self.first_name_ar} {self.last_name_ar}".strip()
        return self.full_name


class AuditLog(models.Model):
    """
    سجل التدقيق - Audit trail for all changes
    """
    ACTION_TYPES = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('view', _('View')),
        ('approve', _('Approve')),
        ('reject', _('Reject')),
        ('submit', _('Submit')),
        ('export', _('Export')),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='audit_logs',
        verbose_name=_('User')
    )
    action = models.CharField(_('Action'), max_length=20, choices=ACTION_TYPES)
    
    # Generic relation to any model
    content_type = models.CharField(_('Content Type'), max_length=100)
    object_id = models.CharField(_('Object ID'), max_length=100)
    object_repr = models.CharField(_('Object Representation'), max_length=500)
    
    # Change details
    changes = models.JSONField(_('Changes'), default=dict, blank=True)
    
    # Request info
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.object_repr}"


class Setting(models.Model):
    """
    الإعدادات - System settings
    """
    SETTING_TYPES = [
        ('string', _('String')),
        ('number', _('Number')),
        ('boolean', _('Boolean')),
        ('json', _('JSON')),
    ]
    
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='settings',
        verbose_name=_('Organization')
    )
    key = models.CharField(_('Key'), max_length=100)
    value = models.TextField(_('Value'))
    value_type = models.CharField(_('Value Type'), max_length=20, choices=SETTING_TYPES, default='string')
    description = models.TextField(_('Description'), blank=True)
    
    is_system = models.BooleanField(_('System Setting'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Setting')
        verbose_name_plural = _('Settings')
        unique_together = ['organization', 'key']
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"
