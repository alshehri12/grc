"""
Governance models for the GRC system.
Policies, procedures, frameworks, and document control.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class PolicyCategory(models.Model):
    """
    تصنيف السياسة - Policy category
    """
    name = models.CharField(_('Category Name'), max_length=200)
    name_ar = models.CharField(_('اسم التصنيف'), max_length=200, blank=True)
    code = models.CharField(_('Category Code'), max_length=50, unique=True)
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='children',
        verbose_name=_('Parent Category')
    )
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Policy Category')
        verbose_name_plural = _('Policy Categories')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Policy(models.Model):
    """
    السياسة - Policy document
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending_review', _('Pending Review')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('published', _('Published')),
        ('retired', _('Retired')),
    ]
    
    CLASSIFICATION_CHOICES = [
        ('public', _('Public')),
        ('internal', _('Internal')),
        ('confidential', _('Confidential')),
        ('restricted', _('Restricted')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='policies',
        verbose_name=_('Organization')
    )
    category = models.ForeignKey(
        PolicyCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='policies',
        verbose_name=_('Category')
    )
    
    # Identification
    policy_id = models.CharField(_('Policy ID'), max_length=50)
    title = models.CharField(_('Title'), max_length=300)
    title_ar = models.CharField(_('العنوان'), max_length=300, blank=True)
    
    # Content
    purpose = models.TextField(_('Purpose'))
    purpose_ar = models.TextField(_('الغرض'), blank=True)
    scope = models.TextField(_('Scope'))
    scope_ar = models.TextField(_('النطاق'), blank=True)
    policy_statement = models.TextField(_('Policy Statement'))
    policy_statement_ar = models.TextField(_('بيان السياسة'), blank=True)
    
    # Metadata
    version = models.CharField(_('Version'), max_length=20, default='1.0')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    classification = models.CharField(
        _('Classification'), 
        max_length=20, 
        choices=CLASSIFICATION_CHOICES, 
        default='internal'
    )
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_policies',
        verbose_name=_('Policy Owner')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='policies',
        verbose_name=_('Responsible Department')
    )
    
    # Review cycle
    effective_date = models.DateField(_('Effective Date'), null=True, blank=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    expiry_date = models.DateField(_('Expiry Date'), null=True, blank=True)
    review_frequency_months = models.PositiveIntegerField(_('Review Frequency (Months)'), default=12)
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_policies',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    
    # Attachments
    document = models.FileField(_('Document'), upload_to='policies/documents/', blank=True, null=True)
    
    # Related controls
    related_controls = models.ManyToManyField(
        'compliance.Control', 
        blank=True,
        related_name='policies',
        verbose_name=_('Related Controls')
    )
    
    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_policies',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Policy')
        verbose_name_plural = _('Policies')
        ordering = ['-updated_at']
        unique_together = ['organization', 'policy_id']
    
    def __str__(self):
        return f"{self.policy_id}: {self.title}"


class PolicyVersion(models.Model):
    """
    إصدار السياسة - Policy version history
    """
    policy = models.ForeignKey(
        Policy, 
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name=_('Policy')
    )
    version = models.CharField(_('Version'), max_length=20)
    
    # Snapshot of content at this version
    title = models.CharField(_('Title'), max_length=300)
    title_ar = models.CharField(_('العنوان'), max_length=300, blank=True)
    purpose = models.TextField(_('Purpose'))
    purpose_ar = models.TextField(_('الغرض'), blank=True)
    scope = models.TextField(_('Scope'))
    scope_ar = models.TextField(_('النطاق'), blank=True)
    policy_statement = models.TextField(_('Policy Statement'))
    policy_statement_ar = models.TextField(_('بيان السياسة'), blank=True)
    
    # Document at this version
    document = models.FileField(_('Document'), upload_to='policies/versions/', blank=True, null=True)
    
    change_summary = models.TextField(_('Change Summary'), blank=True)
    change_summary_ar = models.TextField(_('ملخص التغييرات'), blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_policy_versions',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Policy Version')
        verbose_name_plural = _('Policy Versions')
        ordering = ['-created_at']
        unique_together = ['policy', 'version']
    
    def __str__(self):
        return f"{self.policy.policy_id} v{self.version}"


class PolicyAcknowledgment(models.Model):
    """
    إقرار السياسة - Policy acknowledgment by users
    """
    policy = models.ForeignKey(
        Policy, 
        on_delete=models.CASCADE,
        related_name='acknowledgments',
        verbose_name=_('Policy')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='policy_acknowledgments',
        verbose_name=_('User')
    )
    version = models.CharField(_('Acknowledged Version'), max_length=20)
    
    acknowledged_at = models.DateTimeField(_('Acknowledged At'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Policy Acknowledgment')
        verbose_name_plural = _('Policy Acknowledgments')
        ordering = ['-acknowledged_at']
        unique_together = ['policy', 'user', 'version']
    
    def __str__(self):
        return f"{self.user} acknowledged {self.policy.policy_id}"


class Procedure(models.Model):
    """
    الإجراء - Procedure document
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending_review', _('Pending Review')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('published', _('Published')),
        ('retired', _('Retired')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='procedures',
        verbose_name=_('Organization')
    )
    
    # Related policy
    policy = models.ForeignKey(
        Policy, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='procedures',
        verbose_name=_('Related Policy')
    )
    
    # Identification
    procedure_id = models.CharField(_('Procedure ID'), max_length=50)
    title = models.CharField(_('Title'), max_length=300)
    title_ar = models.CharField(_('العنوان'), max_length=300, blank=True)
    
    # Content
    purpose = models.TextField(_('Purpose'))
    purpose_ar = models.TextField(_('الغرض'), blank=True)
    scope = models.TextField(_('Scope'))
    scope_ar = models.TextField(_('النطاق'), blank=True)
    procedure_steps = models.TextField(_('Procedure Steps'))
    procedure_steps_ar = models.TextField(_('خطوات الإجراء'), blank=True)
    
    # Metadata
    version = models.CharField(_('Version'), max_length=20, default='1.0')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_procedures',
        verbose_name=_('Procedure Owner')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='procedures',
        verbose_name=_('Responsible Department')
    )
    
    # Review cycle
    effective_date = models.DateField(_('Effective Date'), null=True, blank=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    review_frequency_months = models.PositiveIntegerField(_('Review Frequency (Months)'), default=12)
    
    # Attachments
    document = models.FileField(_('Document'), upload_to='procedures/documents/', blank=True, null=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_procedures',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Procedure')
        verbose_name_plural = _('Procedures')
        ordering = ['-updated_at']
        unique_together = ['organization', 'procedure_id']
    
    def __str__(self):
        return f"{self.procedure_id}: {self.title}"


class Document(models.Model):
    """
    الوثيقة - Controlled document
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('active', _('Active')),
        ('under_review', _('Under Review')),
        ('archived', _('Archived')),
    ]
    
    CLASSIFICATION_CHOICES = [
        ('public', _('Public')),
        ('internal', _('Internal')),
        ('confidential', _('Confidential')),
        ('restricted', _('Restricted')),
    ]
    
    DOCUMENT_TYPES = [
        ('policy', _('Policy')),
        ('procedure', _('Procedure')),
        ('standard', _('Standard')),
        ('guideline', _('Guideline')),
        ('form', _('Form')),
        ('template', _('Template')),
        ('record', _('Record')),
        ('other', _('Other')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('Organization')
    )
    
    # Identification
    document_id = models.CharField(_('Document ID'), max_length=50)
    title = models.CharField(_('Title'), max_length=300)
    title_ar = models.CharField(_('العنوان'), max_length=300, blank=True)
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Metadata
    document_type = models.CharField(_('Document Type'), max_length=20, choices=DOCUMENT_TYPES)
    version = models.CharField(_('Version'), max_length=20, default='1.0')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    classification = models.CharField(
        _('Classification'), 
        max_length=20, 
        choices=CLASSIFICATION_CHOICES, 
        default='internal'
    )
    
    # File
    file = models.FileField(_('File'), upload_to='documents/')
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), null=True, blank=True)
    file_type = models.CharField(_('File Type'), max_length=50, blank=True)
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_documents',
        verbose_name=_('Document Owner')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='documents',
        verbose_name=_('Department')
    )
    
    # Review cycle
    effective_date = models.DateField(_('Effective Date'), null=True, blank=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    expiry_date = models.DateField(_('Expiry Date'), null=True, blank=True)
    
    # Access control
    is_public = models.BooleanField(_('Public Access'), default=False)
    allowed_roles = models.ManyToManyField(
        'core.Role', 
        blank=True,
        related_name='accessible_documents',
        verbose_name=_('Allowed Roles')
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_documents',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-updated_at']
        unique_together = ['organization', 'document_id']
    
    def __str__(self):
        return f"{self.document_id}: {self.title}"
