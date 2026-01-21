"""
Risk Management models for the GRC system.
Risk register, assessments, treatments, and risk matrix.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AssetCategory(models.Model):
    """
    تصنيف الأصول - Asset category
    """
    name = models.CharField(_('Category Name'), max_length=200)
    name_ar = models.CharField(_('اسم التصنيف'), max_length=200, blank=True)
    code = models.CharField(_('Category Code'), max_length=50, unique=True)
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Asset Category')
        verbose_name_plural = _('Asset Categories')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Asset(models.Model):
    """
    الأصل - Information asset
    """
    CRITICALITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('retired', _('Retired')),
        ('under_review', _('Under Review')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='assets',
        verbose_name=_('Organization')
    )
    category = models.ForeignKey(
        AssetCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='assets',
        verbose_name=_('Category')
    )
    
    # Identification
    asset_id = models.CharField(_('Asset ID'), max_length=50)
    name = models.CharField(_('Asset Name'), max_length=300)
    name_ar = models.CharField(_('اسم الأصل'), max_length=300, blank=True)
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Classification
    criticality = models.CharField(_('Criticality'), max_length=20, choices=CRITICALITY_CHOICES, default='medium')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_assets',
        verbose_name=_('Asset Owner')
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='custodian_assets',
        verbose_name=_('Asset Custodian')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assets',
        verbose_name=_('Department')
    )
    
    # Value assessment
    confidentiality_value = models.PositiveIntegerField(_('Confidentiality Value (1-5)'), default=3)
    integrity_value = models.PositiveIntegerField(_('Integrity Value (1-5)'), default=3)
    availability_value = models.PositiveIntegerField(_('Availability Value (1-5)'), default=3)
    
    # Location
    location = models.CharField(_('Location'), max_length=200, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_assets',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Asset')
        verbose_name_plural = _('Assets')
        ordering = ['-criticality', 'name']
        unique_together = ['organization', 'asset_id']
    
    def __str__(self):
        return f"{self.asset_id}: {self.name}"
    
    @property
    def asset_value(self):
        """Calculate overall asset value based on CIA"""
        return max(self.confidentiality_value, self.integrity_value, self.availability_value)


class RiskCategory(models.Model):
    """
    تصنيف المخاطر - Risk category
    """
    name = models.CharField(_('Category Name'), max_length=200)
    name_ar = models.CharField(_('اسم التصنيف'), max_length=200, blank=True)
    code = models.CharField(_('Category Code'), max_length=50, unique=True)
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    color = models.CharField(_('Color'), max_length=7, default='#6c757d')
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='children',
        verbose_name=_('Parent Category')
    )
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Risk Category')
        verbose_name_plural = _('Risk Categories')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Risk(models.Model):
    """
    المخاطر - Risk register entry
    """
    STATUS_CHOICES = [
        ('identified', _('Identified')),
        ('pending_approval', _('Pending Approval')),
        ('assessed', _('Assessed')),
        ('treating', _('Under Treatment')),
        ('monitoring', _('Monitoring')),
        ('closed', _('Closed')),
    ]
    
    RISK_TYPES = [
        ('strategic', _('Strategic')),
        ('operational', _('Operational')),
        ('financial', _('Financial')),
        ('compliance', _('Compliance')),
        ('cyber', _('Cybersecurity')),
        ('reputational', _('Reputational')),
        ('other', _('Other')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='risks',
        verbose_name=_('Organization')
    )
    category = models.ForeignKey(
        RiskCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='risks',
        verbose_name=_('Category')
    )
    
    # Identification
    risk_id = models.CharField(_('Risk ID'), max_length=50)
    title = models.CharField(_('Risk Title'), max_length=300)
    title_ar = models.CharField(_('عنوان المخاطر'), max_length=300, blank=True)
    description = models.TextField(_('Risk Description'), blank=True)
    description_ar = models.TextField(_('وصف المخاطر'), blank=True)
    
    risk_type = models.CharField(_('Risk Type'), max_length=20, choices=RISK_TYPES, default='operational')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='identified')
    
    # Source and context
    risk_source = models.TextField(_('Risk Source'), blank=True)
    risk_source_ar = models.TextField(_('مصدر المخاطر'), blank=True)
    
    # Related assets
    assets = models.ManyToManyField(
        Asset, 
        blank=True,
        related_name='risks',
        verbose_name=_('Related Assets')
    )
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='owned_risks',
        verbose_name=_('Risk Owner')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='risks',
        verbose_name=_('Department')
    )
    
    # Inherent risk (before controls)
    inherent_likelihood = models.PositiveIntegerField(_('Inherent Likelihood (1-5)'), default=3)
    inherent_impact = models.PositiveIntegerField(_('Inherent Impact (1-5)'), default=3)
    
    # Residual risk (after controls)
    residual_likelihood = models.PositiveIntegerField(_('Residual Likelihood (1-5)'), null=True, blank=True)
    residual_impact = models.PositiveIntegerField(_('Residual Impact (1-5)'), null=True, blank=True)
    
    # Target risk (desired state)
    target_likelihood = models.PositiveIntegerField(_('Target Likelihood (1-5)'), null=True, blank=True)
    target_impact = models.PositiveIntegerField(_('Target Impact (1-5)'), null=True, blank=True)
    
    # Dates
    identified_date = models.DateField(_('Identified Date'), auto_now_add=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    
    # Related controls
    controls = models.ManyToManyField(
        'compliance.Control', 
        blank=True,
        related_name='mitigated_risks',
        verbose_name=_('Mitigating Controls')
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_risks',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Risk')
        verbose_name_plural = _('Risks')
        ordering = ['-inherent_likelihood', '-inherent_impact']
        unique_together = ['organization', 'risk_id']
    
    def __str__(self):
        return f"{self.risk_id}: {self.title}"
    
    @property
    def inherent_risk_score(self):
        return self.inherent_likelihood * self.inherent_impact
    
    @property
    def residual_risk_score(self):
        if self.residual_likelihood and self.residual_impact:
            return self.residual_likelihood * self.residual_impact
        return None
    
    @property
    def risk_level(self):
        """Get risk level based on inherent score"""
        score = self.inherent_risk_score
        if score >= 20:
            return 'critical'
        elif score >= 12:
            return 'high'
        elif score >= 6:
            return 'medium'
        else:
            return 'low'


class RiskAssessment(models.Model):
    """
    تقييم المخاطر - Risk assessment record
    """
    ASSESSMENT_TYPES = [
        ('initial', _('Initial Assessment')),
        ('periodic', _('Periodic Review')),
        ('incident', _('Post-Incident')),
        ('change', _('Change-Triggered')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('approved', _('Approved')),
    ]
    
    risk = models.ForeignKey(
        Risk, 
        on_delete=models.CASCADE,
        related_name='assessments',
        verbose_name=_('Risk')
    )
    
    assessment_type = models.CharField(_('Assessment Type'), max_length=20, choices=ASSESSMENT_TYPES, default='periodic')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Assessment date
    assessment_date = models.DateField(_('Assessment Date'))
    
    # Likelihood assessment
    likelihood_score = models.PositiveIntegerField(_('Likelihood Score (1-5)'))
    likelihood_rationale = models.TextField(_('Likelihood Rationale'))
    likelihood_rationale_ar = models.TextField(_('مبررات الاحتمالية'), blank=True)
    
    # Impact assessment
    impact_score = models.PositiveIntegerField(_('Impact Score (1-5)'))
    impact_rationale = models.TextField(_('Impact Rationale'))
    impact_rationale_ar = models.TextField(_('مبررات الأثر'), blank=True)
    
    # Control effectiveness
    control_effectiveness = models.PositiveIntegerField(
        _('Control Effectiveness (%)'), 
        default=0,
        help_text=_('Percentage of risk reduced by controls')
    )
    
    # Findings
    findings = models.TextField(_('Assessment Findings'), blank=True)
    findings_ar = models.TextField(_('نتائج التقييم'), blank=True)
    recommendations = models.TextField(_('Recommendations'), blank=True)
    recommendations_ar = models.TextField(_('التوصيات'), blank=True)
    
    # Assessor
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='risk_assessments',
        verbose_name=_('Assessor')
    )
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_risk_assessments',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Risk Assessment')
        verbose_name_plural = _('Risk Assessments')
        ordering = ['-assessment_date']
    
    def __str__(self):
        return f"Assessment: {self.risk.risk_id} ({self.assessment_date})"
    
    @property
    def risk_score(self):
        return self.likelihood_score * self.impact_score


class RiskTreatment(models.Model):
    """
    معالجة المخاطر - Risk treatment plan
    """
    TREATMENT_OPTIONS = [
        ('mitigate', _('Mitigate')),
        ('transfer', _('Transfer')),
        ('accept', _('Accept')),
        ('avoid', _('Avoid')),
    ]
    
    STATUS_CHOICES = [
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('deferred', _('Deferred')),
        ('cancelled', _('Cancelled')),
    ]
    
    risk = models.ForeignKey(
        Risk, 
        on_delete=models.CASCADE,
        related_name='treatments',
        verbose_name=_('Risk')
    )
    
    # Treatment details
    treatment_option = models.CharField(_('Treatment Option'), max_length=20, choices=TREATMENT_OPTIONS)
    title = models.CharField(_('Treatment Title'), max_length=300)
    title_ar = models.CharField(_('عنوان المعالجة'), max_length=300, blank=True)
    description = models.TextField(_('Treatment Description'))
    description_ar = models.TextField(_('وصف المعالجة'), blank=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Expected outcome
    expected_residual_likelihood = models.PositiveIntegerField(
        _('Expected Residual Likelihood'), 
        null=True, 
        blank=True
    )
    expected_residual_impact = models.PositiveIntegerField(
        _('Expected Residual Impact'), 
        null=True, 
        blank=True
    )
    
    # Resources
    estimated_cost = models.DecimalField(
        _('Estimated Cost'), 
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Assignment
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_treatments',
        verbose_name=_('Treatment Owner')
    )
    
    # Dates
    start_date = models.DateField(_('Start Date'), null=True, blank=True)
    due_date = models.DateField(_('Due Date'), null=True, blank=True)
    completed_date = models.DateField(_('Completed Date'), null=True, blank=True)
    
    # Progress
    progress_percentage = models.PositiveIntegerField(_('Progress (%)'), default=0)
    progress_notes = models.TextField(_('Progress Notes'), blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_treatments',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Risk Treatment')
        verbose_name_plural = _('Risk Treatments')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.treatment_option}: {self.title}"


class RiskAcceptance(models.Model):
    """
    قبول المخاطر - Risk acceptance record
    """
    STATUS_CHOICES = [
        ('pending', _('Pending Approval')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('expired', _('Expired')),
    ]
    
    risk = models.ForeignKey(
        Risk, 
        on_delete=models.CASCADE,
        related_name='acceptances',
        verbose_name=_('Risk')
    )
    
    # Acceptance details
    justification = models.TextField(_('Justification'))
    justification_ar = models.TextField(_('المبررات'), blank=True)
    conditions = models.TextField(_('Acceptance Conditions'), blank=True)
    conditions_ar = models.TextField(_('شروط القبول'), blank=True)
    
    # Risk level at acceptance
    accepted_likelihood = models.PositiveIntegerField(_('Accepted Likelihood'))
    accepted_impact = models.PositiveIntegerField(_('Accepted Impact'))
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Validity
    valid_from = models.DateField(_('Valid From'))
    valid_until = models.DateField(_('Valid Until'))
    
    # Requester
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='requested_acceptances',
        verbose_name=_('Requested By')
    )
    requested_date = models.DateField(_('Requested Date'), auto_now_add=True)
    
    # Approver
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_acceptances',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    approval_comments = models.TextField(_('Approval Comments'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Risk Acceptance')
        verbose_name_plural = _('Risk Acceptances')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Acceptance: {self.risk.risk_id}"
    
    @property
    def accepted_risk_score(self):
        return self.accepted_likelihood * self.accepted_impact
