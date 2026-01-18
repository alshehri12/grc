"""
Compliance models for the GRC system.
Controls, audits, evidence, and gap analysis.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ControlFramework(models.Model):
    """
    إطار الضوابط - Compliance framework (ISO, NCA, SAMA, etc.)
    """
    name = models.CharField(_('Framework Name'), max_length=200)
    name_ar = models.CharField(_('اسم الإطار'), max_length=200, blank=True)
    code = models.CharField(_('Framework Code'), max_length=50, unique=True)
    version = models.CharField(_('Version'), max_length=20)
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Framework metadata
    issuing_body = models.CharField(_('Issuing Body'), max_length=200, blank=True)
    issuing_body_ar = models.CharField(_('الجهة المصدرة'), max_length=200, blank=True)
    publication_date = models.DateField(_('Publication Date'), null=True, blank=True)
    
    # Is this a regulatory requirement?
    is_mandatory = models.BooleanField(_('Mandatory'), default=False)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Control Framework')
        verbose_name_plural = _('Control Frameworks')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.version})"


class ControlDomain(models.Model):
    """
    مجال الضوابط - Control domain/category within a framework
    """
    framework = models.ForeignKey(
        ControlFramework, 
        on_delete=models.CASCADE,
        related_name='domains',
        verbose_name=_('Framework')
    )
    
    code = models.CharField(_('Domain Code'), max_length=50)
    name = models.CharField(_('Domain Name'), max_length=300)
    name_ar = models.CharField(_('اسم المجال'), max_length=300, blank=True)
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='subdomains',
        verbose_name=_('Parent Domain')
    )
    order = models.PositiveIntegerField(_('Order'), default=0)
    
    class Meta:
        verbose_name = _('Control Domain')
        verbose_name_plural = _('Control Domains')
        ordering = ['framework', 'order', 'code']
        unique_together = ['framework', 'code']
    
    def __str__(self):
        return f"{self.framework.code} - {self.code}: {self.name}"


class Control(models.Model):
    """
    الضابط - Individual control
    """
    CONTROL_TYPES = [
        ('preventive', _('Preventive')),
        ('detective', _('Detective')),
        ('corrective', _('Corrective')),
        ('compensating', _('Compensating')),
    ]
    
    IMPLEMENTATION_STATUS = [
        ('not_implemented', _('Not Implemented')),
        ('partially_implemented', _('Partially Implemented')),
        ('implemented', _('Implemented')),
        ('not_applicable', _('Not Applicable')),
    ]
    
    domain = models.ForeignKey(
        ControlDomain, 
        on_delete=models.CASCADE,
        related_name='controls',
        verbose_name=_('Domain')
    )
    
    # Identification
    control_id = models.CharField(_('Control ID'), max_length=50)
    title = models.CharField(_('Control Title'), max_length=500)
    title_ar = models.CharField(_('عنوان الضابط'), max_length=500, blank=True)
    
    description = models.TextField(_('Control Description'), blank=True)
    description_ar = models.TextField(_('وصف الضابط'), blank=True)
    
    # Control details
    control_type = models.CharField(_('Control Type'), max_length=20, choices=CONTROL_TYPES, default='preventive')
    
    # Implementation guidance
    implementation_guidance = models.TextField(_('Implementation Guidance'), blank=True)
    implementation_guidance_ar = models.TextField(_('إرشادات التطبيق'), blank=True)
    
    # Testing guidance
    testing_guidance = models.TextField(_('Testing Guidance'), blank=True)
    testing_guidance_ar = models.TextField(_('إرشادات الاختبار'), blank=True)
    
    # Evidence requirements
    evidence_requirements = models.TextField(_('Evidence Requirements'), blank=True)
    evidence_requirements_ar = models.TextField(_('متطلبات الأدلة'), blank=True)
    
    order = models.PositiveIntegerField(_('Order'), default=0)
    
    # Cross-framework mapping
    mapped_controls = models.ManyToManyField(
        'self', 
        blank=True,
        symmetrical=True,
        verbose_name=_('Mapped Controls')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Control')
        verbose_name_plural = _('Controls')
        ordering = ['domain', 'order', 'control_id']
        unique_together = ['domain', 'control_id']
    
    def __str__(self):
        return f"{self.control_id}: {self.title[:50]}"
    
    @property
    def framework(self):
        return self.domain.framework


class ControlImplementation(models.Model):
    """
    تطبيق الضابط - Control implementation status per organization
    """
    IMPLEMENTATION_STATUS = [
        ('not_implemented', _('Not Implemented')),
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('partially_implemented', _('Partially Implemented')),
        ('implemented', _('Implemented')),
        ('not_applicable', _('Not Applicable')),
    ]
    
    MATURITY_LEVELS = [
        (0, _('0 - Non-existent')),
        (1, _('1 - Initial')),
        (2, _('2 - Managed')),
        (3, _('3 - Defined')),
        (4, _('4 - Quantitatively Managed')),
        (5, _('5 - Optimizing')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='control_implementations',
        verbose_name=_('Organization')
    )
    control = models.ForeignKey(
        Control, 
        on_delete=models.CASCADE,
        related_name='implementations',
        verbose_name=_('Control')
    )
    
    # Status
    status = models.CharField(_('Status'), max_length=30, choices=IMPLEMENTATION_STATUS, default='not_implemented')
    maturity_level = models.PositiveIntegerField(_('Maturity Level'), choices=MATURITY_LEVELS, default=0)
    
    # Implementation details
    implementation_details = models.TextField(_('Implementation Details'), blank=True)
    implementation_details_ar = models.TextField(_('تفاصيل التطبيق'), blank=True)
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='owned_control_implementations',
        verbose_name=_('Control Owner')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='control_implementations',
        verbose_name=_('Responsible Department')
    )
    
    # Testing
    last_tested_date = models.DateField(_('Last Tested Date'), null=True, blank=True)
    next_test_date = models.DateField(_('Next Test Date'), null=True, blank=True)
    test_frequency_months = models.PositiveIntegerField(_('Test Frequency (Months)'), default=12)
    
    # Effectiveness
    effectiveness_rating = models.PositiveIntegerField(
        _('Effectiveness Rating (1-5)'), 
        null=True, 
        blank=True
    )
    
    # Gap information
    gap_description = models.TextField(_('Gap Description'), blank=True)
    gap_description_ar = models.TextField(_('وصف الفجوة'), blank=True)
    remediation_plan = models.TextField(_('Remediation Plan'), blank=True)
    remediation_plan_ar = models.TextField(_('خطة المعالجة'), blank=True)
    target_date = models.DateField(_('Target Implementation Date'), null=True, blank=True)
    
    # Notes
    notes = models.TextField(_('Notes'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Control Implementation')
        verbose_name_plural = _('Control Implementations')
        unique_together = ['organization', 'control']
    
    def __str__(self):
        return f"{self.organization.code} - {self.control.control_id}"


class Audit(models.Model):
    """
    التدقيق - Audit record
    """
    AUDIT_TYPES = [
        ('internal', _('Internal Audit')),
        ('external', _('External Audit')),
        ('regulatory', _('Regulatory Audit')),
        ('certification', _('Certification Audit')),
        ('surveillance', _('Surveillance Audit')),
    ]
    
    STATUS_CHOICES = [
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('fieldwork', _('Fieldwork')),
        ('reporting', _('Reporting')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='audits',
        verbose_name=_('Organization')
    )
    
    # Identification
    audit_id = models.CharField(_('Audit ID'), max_length=50)
    title = models.CharField(_('Audit Title'), max_length=300)
    title_ar = models.CharField(_('عنوان التدقيق'), max_length=300, blank=True)
    
    audit_type = models.CharField(_('Audit Type'), max_length=20, choices=AUDIT_TYPES, default='internal')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Scope
    scope = models.TextField(_('Audit Scope'), blank=True)
    scope_ar = models.TextField(_('نطاق التدقيق'), blank=True)
    objectives = models.TextField(_('Audit Objectives'), blank=True)
    objectives_ar = models.TextField(_('أهداف التدقيق'), blank=True)
    
    # Frameworks/controls being audited
    frameworks = models.ManyToManyField(
        ControlFramework, 
        blank=True,
        related_name='audits',
        verbose_name=_('Frameworks Audited')
    )
    controls = models.ManyToManyField(
        Control, 
        blank=True,
        related_name='audits',
        verbose_name=_('Controls Audited')
    )
    
    # Departments being audited
    departments = models.ManyToManyField(
        'core.Department', 
        blank=True,
        related_name='audits',
        verbose_name=_('Departments Audited')
    )
    
    # Audit team
    lead_auditor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='led_audits',
        verbose_name=_('Lead Auditor')
    )
    auditors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True,
        related_name='audits',
        verbose_name=_('Audit Team')
    )
    
    # External auditor information
    external_firm = models.CharField(_('External Audit Firm'), max_length=200, blank=True)
    
    # Schedule
    planned_start_date = models.DateField(_('Planned Start Date'))
    planned_end_date = models.DateField(_('Planned End Date'))
    actual_start_date = models.DateField(_('Actual Start Date'), null=True, blank=True)
    actual_end_date = models.DateField(_('Actual End Date'), null=True, blank=True)
    
    # Criteria
    audit_criteria = models.TextField(_('Audit Criteria'), blank=True)
    audit_criteria_ar = models.TextField(_('معايير التدقيق'), blank=True)
    
    # Methodology
    methodology = models.TextField(_('Audit Methodology'), blank=True)
    methodology_ar = models.TextField(_('منهجية التدقيق'), blank=True)
    
    # Report
    report_date = models.DateField(_('Report Date'), null=True, blank=True)
    executive_summary = models.TextField(_('Executive Summary'), blank=True)
    executive_summary_ar = models.TextField(_('الملخص التنفيذي'), blank=True)
    conclusion = models.TextField(_('Conclusion'), blank=True)
    conclusion_ar = models.TextField(_('الخلاصة'), blank=True)
    
    report_document = models.FileField(_('Audit Report'), upload_to='audits/reports/', blank=True, null=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_audits',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Audit')
        verbose_name_plural = _('Audits')
        ordering = ['-planned_start_date']
        unique_together = ['organization', 'audit_id']
    
    def __str__(self):
        return f"{self.audit_id}: {self.title}"


class AuditFinding(models.Model):
    """
    نتيجة التدقيق - Audit finding
    """
    FINDING_TYPES = [
        ('major_nc', _('Major Non-Conformity')),
        ('minor_nc', _('Minor Non-Conformity')),
        ('observation', _('Observation')),
        ('opportunity', _('Opportunity for Improvement')),
        ('positive', _('Positive Finding')),
    ]
    
    STATUS_CHOICES = [
        ('open', _('Open')),
        ('in_progress', _('In Progress')),
        ('pending_verification', _('Pending Verification')),
        ('closed', _('Closed')),
        ('overdue', _('Overdue')),
    ]
    
    audit = models.ForeignKey(
        Audit, 
        on_delete=models.CASCADE,
        related_name='findings',
        verbose_name=_('Audit')
    )
    
    # Identification
    finding_id = models.CharField(_('Finding ID'), max_length=50)
    title = models.CharField(_('Finding Title'), max_length=300)
    title_ar = models.CharField(_('عنوان النتيجة'), max_length=300, blank=True)
    
    finding_type = models.CharField(_('Finding Type'), max_length=20, choices=FINDING_TYPES, default='observation')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Details
    description = models.TextField(_('Finding Description'), blank=True)
    description_ar = models.TextField(_('وصف النتيجة'), blank=True)
    
    # Reference
    criteria_reference = models.CharField(_('Criteria Reference'), max_length=200, blank=True)
    control = models.ForeignKey(
        Control, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='findings',
        verbose_name=_('Related Control')
    )
    
    # Evidence
    evidence_collected = models.TextField(_('Evidence Collected'), blank=True)
    evidence_collected_ar = models.TextField(_('الأدلة المجمعة'), blank=True)
    
    # Risk rating
    risk_rating = models.CharField(_('Risk Rating'), max_length=20, blank=True)
    
    # Recommendation
    recommendation = models.TextField(_('Recommendation'), blank=True)
    recommendation_ar = models.TextField(_('التوصية'), blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_findings',
        verbose_name=_('Assigned To')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_findings',
        verbose_name=_('Responsible Department')
    )
    
    # Due date
    due_date = models.DateField(_('Due Date'), null=True, blank=True)
    
    # Management response
    management_response = models.TextField(_('Management Response'), blank=True)
    management_response_ar = models.TextField(_('استجابة الإدارة'), blank=True)
    response_date = models.DateField(_('Response Date'), null=True, blank=True)
    
    # Closure
    closure_evidence = models.TextField(_('Closure Evidence'), blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='closed_findings',
        verbose_name=_('Closed By')
    )
    closed_date = models.DateField(_('Closed Date'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Audit Finding')
        verbose_name_plural = _('Audit Findings')
        ordering = ['-finding_type', '-created_at']
        unique_together = ['audit', 'finding_id']
    
    def __str__(self):
        return f"{self.finding_id}: {self.title}"


class CorrectiveAction(models.Model):
    """
    الإجراء التصحيحي - Corrective Action Request (CAR)
    """
    STATUS_CHOICES = [
        ('open', _('Open')),
        ('in_progress', _('In Progress')),
        ('pending_verification', _('Pending Verification')),
        ('verified', _('Verified')),
        ('closed', _('Closed')),
        ('overdue', _('Overdue')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='corrective_actions',
        verbose_name=_('Organization')
    )
    
    # Related finding
    finding = models.ForeignKey(
        AuditFinding, 
        on_delete=models.CASCADE,
        related_name='corrective_actions',
        verbose_name=_('Related Finding')
    )
    
    # Identification
    car_id = models.CharField(_('CAR ID'), max_length=50)
    title = models.CharField(_('Action Title'), max_length=300)
    title_ar = models.CharField(_('عنوان الإجراء'), max_length=300, blank=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(_('Priority'), max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Root cause analysis
    root_cause = models.TextField(_('Root Cause'), blank=True)
    root_cause_ar = models.TextField(_('السبب الجذري'), blank=True)
    
    # Action details
    action_description = models.TextField(_('Action Description'), blank=True)
    action_description_ar = models.TextField(_('وصف الإجراء'), blank=True)
    
    # Assignment
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_corrective_actions',
        verbose_name=_('Action Owner')
    )
    
    # Dates
    target_date = models.DateField(_('Target Completion Date'))
    completed_date = models.DateField(_('Actual Completion Date'), null=True, blank=True)
    
    # Implementation
    implementation_notes = models.TextField(_('Implementation Notes'), blank=True)
    implementation_notes_ar = models.TextField(_('ملاحظات التنفيذ'), blank=True)
    
    # Verification
    verification_method = models.TextField(_('Verification Method'), blank=True)
    verification_method_ar = models.TextField(_('طريقة التحقق'), blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_actions',
        verbose_name=_('Verified By')
    )
    verified_date = models.DateField(_('Verification Date'), null=True, blank=True)
    verification_notes = models.TextField(_('Verification Notes'), blank=True)
    
    # Effectiveness check
    effectiveness_check_date = models.DateField(_('Effectiveness Check Date'), null=True, blank=True)
    is_effective = models.BooleanField(_('Is Effective'), null=True)
    effectiveness_notes = models.TextField(_('Effectiveness Notes'), blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_corrective_actions',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Corrective Action')
        verbose_name_plural = _('Corrective Actions')
        ordering = ['-priority', 'target_date']
        unique_together = ['organization', 'car_id']
    
    def __str__(self):
        return f"{self.car_id}: {self.title}"


class Evidence(models.Model):
    """
    الدليل - Compliance evidence
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
        ('expired', _('Expired')),
    ]
    
    EVIDENCE_TYPES = [
        ('document', _('Document')),
        ('screenshot', _('Screenshot')),
        ('log', _('System Log')),
        ('report', _('Report')),
        ('configuration', _('Configuration')),
        ('interview', _('Interview Notes')),
        ('observation', _('Observation')),
        ('other', _('Other')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='evidences',
        verbose_name=_('Organization')
    )
    
    # Related control implementation
    control_implementation = models.ForeignKey(
        ControlImplementation, 
        on_delete=models.CASCADE,
        related_name='evidences',
        verbose_name=_('Control Implementation')
    )
    
    # Identification
    evidence_id = models.CharField(_('Evidence ID'), max_length=50)
    title = models.CharField(_('Evidence Title'), max_length=300)
    title_ar = models.CharField(_('عنوان الدليل'), max_length=300, blank=True)
    
    evidence_type = models.CharField(_('Evidence Type'), max_length=20, choices=EVIDENCE_TYPES, default='document')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # File
    file = models.FileField(_('Evidence File'), upload_to='evidence/')
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), null=True, blank=True)
    
    # Validity
    collection_date = models.DateField(_('Collection Date'))
    valid_from = models.DateField(_('Valid From'))
    valid_until = models.DateField(_('Valid Until'))
    
    # Submitted by
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='submitted_evidences',
        verbose_name=_('Submitted By')
    )
    submitted_date = models.DateField(_('Submitted Date'), null=True, blank=True)
    
    # Review
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_evidences',
        verbose_name=_('Reviewed By')
    )
    reviewed_date = models.DateField(_('Reviewed Date'), null=True, blank=True)
    review_notes = models.TextField(_('Review Notes'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Evidence')
        verbose_name_plural = _('Evidences')
        ordering = ['-collection_date']
        unique_together = ['organization', 'evidence_id']
    
    def __str__(self):
        return f"{self.evidence_id}: {self.title}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return self.valid_until < timezone.now().date()


class GapAssessment(models.Model):
    """
    تقييم الفجوات - Gap assessment
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('approved', _('Approved')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='gap_assessments',
        verbose_name=_('Organization')
    )
    framework = models.ForeignKey(
        ControlFramework, 
        on_delete=models.CASCADE,
        related_name='gap_assessments',
        verbose_name=_('Framework')
    )
    
    # Identification
    assessment_id = models.CharField(_('Assessment ID'), max_length=50)
    title = models.CharField(_('Assessment Title'), max_length=300)
    title_ar = models.CharField(_('عنوان التقييم'), max_length=300, blank=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Assessment details
    assessment_date = models.DateField(_('Assessment Date'), null=True, blank=True)
    scope = models.TextField(_('Assessment Scope'), blank=True)
    scope_ar = models.TextField(_('نطاق التقييم'), blank=True)
    
    # Results summary
    total_controls = models.PositiveIntegerField(_('Total Controls'), default=0)
    implemented_controls = models.PositiveIntegerField(_('Implemented Controls'), default=0)
    partially_implemented = models.PositiveIntegerField(_('Partially Implemented'), default=0)
    not_implemented = models.PositiveIntegerField(_('Not Implemented'), default=0)
    not_applicable = models.PositiveIntegerField(_('Not Applicable'), default=0)
    
    compliance_score = models.DecimalField(
        _('Compliance Score (%)'), 
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    maturity_score = models.DecimalField(
        _('Maturity Score'), 
        max_digits=3, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Findings
    executive_summary = models.TextField(_('Executive Summary'), blank=True)
    executive_summary_ar = models.TextField(_('الملخص التنفيذي'), blank=True)
    key_gaps = models.TextField(_('Key Gaps Identified'), blank=True)
    key_gaps_ar = models.TextField(_('الفجوات الرئيسية'), blank=True)
    recommendations = models.TextField(_('Recommendations'), blank=True)
    recommendations_ar = models.TextField(_('التوصيات'), blank=True)
    
    # Remediation plan
    remediation_plan = models.TextField(_('Remediation Plan'), blank=True)
    remediation_plan_ar = models.TextField(_('خطة المعالجة'), blank=True)
    
    # Report
    report_document = models.FileField(_('Assessment Report'), upload_to='gap_assessments/', blank=True, null=True)
    
    # Assessor
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='conducted_gap_assessments',
        verbose_name=_('Assessor')
    )
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_gap_assessments',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Gap Assessment')
        verbose_name_plural = _('Gap Assessments')
        ordering = ['-assessment_date']
        unique_together = ['organization', 'assessment_id']
    
    def __str__(self):
        return f"{self.assessment_id}: {self.title}"
    
    def calculate_compliance_score(self):
        """Calculate compliance score based on control implementations"""
        applicable = self.total_controls - self.not_applicable
        if applicable > 0:
            weighted_score = (self.implemented_controls * 100 + self.partially_implemented * 50) / applicable
            return round(weighted_score, 2)
        return 0
