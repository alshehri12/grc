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
    # When True the residual scores are derived from linked control effectiveness and are
    # recalculated automatically; a manual residual assessment switches this off.
    residual_auto = models.BooleanField(_('Residual Calculated From Controls'), default=True)
    
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
    
    def clean(self):
        """Validate risk scores are within acceptable range."""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate likelihood/impact ranges (1-5)
        for field in ['inherent_likelihood', 'inherent_impact', 'residual_likelihood', 
                      'residual_impact', 'target_likelihood', 'target_impact']:
            value = getattr(self, field, None)
            if value is not None and (value < 1 or value > 5):
                errors[field] = f'{field.replace("_", " ").title()} must be between 1 and 5'
        
        # Validate residual <= inherent (controls should reduce risk)
        if self.residual_likelihood and self.inherent_likelihood:
            if self.residual_likelihood > self.inherent_likelihood:
                errors['residual_likelihood'] = 'Residual likelihood should not exceed inherent likelihood'
        
        if self.residual_impact and self.inherent_impact:
            if self.residual_impact > self.inherent_impact:
                errors['residual_impact'] = 'Residual impact should not exceed inherent impact'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def inherent_risk_score(self):
        """Calculate inherent risk score (before controls)."""
        return self.inherent_likelihood * self.inherent_impact
    
    @property
    def residual_risk_score(self):
        """Calculate residual risk score (after controls)."""
        if self.residual_likelihood and self.residual_impact:
            return self.residual_likelihood * self.residual_impact
        return None
    
    @property
    def target_risk_score(self):
        """Calculate target risk score (desired state)."""
        if self.target_likelihood and self.target_impact:
            return self.target_likelihood * self.target_impact
        return None
    
    @property
    def risk_level(self):
        """Inherent risk level from the organization's single risk-matrix thresholds."""
        from risk.utils import get_risk_level
        return get_risk_level(self.inherent_risk_score, self.organization_id)

    @property
    def residual_risk_level(self):
        """Residual risk level from the same thresholds (None when not yet assessed)."""
        from risk.utils import get_risk_level
        return get_risk_level(self.residual_risk_score, self.organization_id)

    @property
    def appetite_status(self):
        """Compare current exposure with the applicable risk appetite statement."""
        from risk.appetite import evaluate_appetite
        return evaluate_appetite(self)
    
    @property
    def risk_reduction_percentage(self):
        """Calculate how much risk has been reduced by controls."""
        if self.residual_risk_score and self.inherent_risk_score:
            reduction = ((self.inherent_risk_score - self.residual_risk_score) / self.inherent_risk_score) * 100
            return round(reduction, 1)
        return None
    
    def calculate_residual_from_controls(self):
        """
        Derive residual likelihood/impact from the linked controls' effectiveness.
        Preventive controls reduce likelihood; detective/corrective controls reduce
        impact (see risk.utils.aggregate_control_effect). Returns the breakdown.
        """
        from risk.utils import aggregate_control_effect, calculate_residual_risk

        if not self.controls.exists():
            # No controls: residual equals inherent (nothing reduces the risk).
            self.residual_likelihood = self.inherent_likelihood
            self.residual_impact = self.inherent_impact
            return {'likelihood_reduction': 0, 'impact_reduction': 0, 'controls': []}

        effect = aggregate_control_effect(self)
        res_likelihood, res_impact, _ = calculate_residual_risk(
            self.inherent_likelihood, self.inherent_impact,
            effect['likelihood_reduction'], effect['impact_reduction'],
        )
        self.residual_likelihood = res_likelihood
        self.residual_impact = res_impact
        return effect

    def apply_control_based_residual(self, save=True):
        """
        Recalculate and persist the control-derived residual (without touching
        updated_at or firing post_save). Returns True when values changed.
        """
        before = (self.residual_likelihood, self.residual_impact)
        self.calculate_residual_from_controls()
        after = (self.residual_likelihood, self.residual_impact)
        if save and after != before:
            type(self).objects.filter(pk=self.pk).update(
                residual_likelihood=self.residual_likelihood, residual_impact=self.residual_impact)
        return after != before
    
    def get_treatment_recommendation(self):
        """Get recommended treatment option based on risk level."""
        from risk.utils import get_treatment_recommendation
        return get_treatment_recommendation(
            self.inherent_risk_score,
            self.residual_risk_score
        )


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


class RiskAppetite(models.Model):
    """
    بيان شهية المخاطر - Board-approved appetite statement per risk category.
    `max_acceptable_score` is the residual score the organization accepts;
    `tolerance_score` is the ceiling above which risks are escalated.
    """
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='risk_appetites',
        verbose_name=_('Organization')
    )
    category = models.ForeignKey(
        RiskCategory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='appetites',
        verbose_name=_('Risk Category'),
        help_text=_('Leave empty for the organization-wide default')
    )
    statement = models.TextField(_('Appetite Statement'))
    statement_ar = models.TextField(_('بيان شهية المخاطر'), blank=True)
    max_acceptable_score = models.PositiveIntegerField(
        _('Appetite (Max Acceptable Residual Score)'), default=12,
        help_text=_('Residual risk score (1-25) the organization is willing to accept')
    )
    tolerance_score = models.PositiveIntegerField(
        _('Tolerance (Escalation Score)'), default=16,
        help_text=_('Residual risk score above which the risk is escalated to senior management')
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_risk_appetites',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    effective_from = models.DateField(_('Effective From'), null=True, blank=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Risk Appetite')
        verbose_name_plural = _('Risk Appetites')
        unique_together = ['organization', 'category']
        ordering = ['organization', 'category__name']

    def __str__(self):
        scope = self.category.name if self.category else 'Organization-wide'
        return f"Appetite ({scope}): <= {self.max_acceptable_score}, tolerance {self.tolerance_score}"

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if not 1 <= self.max_acceptable_score <= 25:
            errors['max_acceptable_score'] = 'Must be between 1 and 25'
        if not 1 <= self.tolerance_score <= 25:
            errors['tolerance_score'] = 'Must be between 1 and 25'
        if self.tolerance_score < self.max_acceptable_score:
            errors['tolerance_score'] = 'Tolerance cannot be lower than appetite'
        if errors:
            raise ValidationError(errors)


class KeyRiskIndicator(models.Model):
    """
    مؤشر المخاطر الرئيسي - Measurable early-warning indicator for a risk.
    """
    DIRECTION_CHOICES = [
        ('up_bad', _('Higher is worse')),
        ('down_bad', _('Lower is worse')),
    ]
    FREQUENCY_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
    ]
    STATUS_CHOICES = [
        ('green', _('Green')),
        ('amber', _('Amber')),
        ('red', _('Red')),
        ('no_data', _('No Data')),
    ]
    FREQUENCY_DAYS = {'daily': 1, 'weekly': 7, 'monthly': 31, 'quarterly': 92}

    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='kris',
        verbose_name=_('Organization')
    )
    risk = models.ForeignKey(
        Risk,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='kris',
        verbose_name=_('Risk')
    )
    category = models.ForeignKey(
        RiskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kris',
        verbose_name=_('Risk Category')
    )
    kri_id = models.CharField(_('KRI ID'), max_length=50)
    name = models.CharField(_('Indicator Name'), max_length=300)
    name_ar = models.CharField(_('اسم المؤشر'), max_length=300, blank=True)
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    unit = models.CharField(_('Unit'), max_length=30, blank=True)
    direction = models.CharField(_('Direction'), max_length=10, choices=DIRECTION_CHOICES, default='up_bad')
    target_value = models.DecimalField(_('Target'), max_digits=14, decimal_places=2, null=True, blank=True)
    warning_threshold = models.DecimalField(_('Warning (Amber) Threshold'), max_digits=14, decimal_places=2)
    critical_threshold = models.DecimalField(_('Critical (Red) Threshold'), max_digits=14, decimal_places=2)
    frequency = models.CharField(_('Measurement Frequency'), max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    data_source = models.CharField(_('Data Source'), max_length=300, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_kris',
        verbose_name=_('Owner')
    )
    is_active = models.BooleanField(_('Active'), default=True)

    # Denormalised latest measurement
    current_value = models.DecimalField(_('Current Value'), max_digits=14, decimal_places=2, null=True, blank=True)
    current_status = models.CharField(_('Current Status'), max_length=10, choices=STATUS_CHOICES, default='no_data')
    last_measured_at = models.DateField(_('Last Measured'), null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_kris',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Key Risk Indicator')
        verbose_name_plural = _('Key Risk Indicators')
        unique_together = ['organization', 'kri_id']
        ordering = ['kri_id']

    def __str__(self):
        return f"{self.kri_id}: {self.name}"

    def status_for(self, value):
        """RAG status for a value according to direction and thresholds."""
        if value is None:
            return 'no_data'
        if self.direction == 'up_bad':
            if value >= self.critical_threshold:
                return 'red'
            if value >= self.warning_threshold:
                return 'amber'
            return 'green'
        if value <= self.critical_threshold:
            return 'red'
        if value <= self.warning_threshold:
            return 'amber'
        return 'green'

    @property
    def measurement_due_date(self):
        if not self.last_measured_at:
            return None
        from datetime import timedelta
        return self.last_measured_at + timedelta(days=self.FREQUENCY_DAYS.get(self.frequency, 31))

    @property
    def is_measurement_overdue(self):
        due = self.measurement_due_date
        if due is None:
            return True
        from django.utils import timezone
        return timezone.localdate() > due

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.warning_threshold is None or self.critical_threshold is None:
            return
        if self.direction == 'up_bad' and self.critical_threshold < self.warning_threshold:
            raise ValidationError({'critical_threshold': 'For "higher is worse" the critical threshold must be >= warning'})
        if self.direction == 'down_bad' and self.critical_threshold > self.warning_threshold:
            raise ValidationError({'critical_threshold': 'For "lower is worse" the critical threshold must be <= warning'})


class KRIMeasurement(models.Model):
    """
    قياس مؤشر المخاطر - One observation of a KRI.
    """
    kri = models.ForeignKey(
        KeyRiskIndicator,
        on_delete=models.CASCADE,
        related_name='measurements',
        verbose_name=_('KRI')
    )
    value = models.DecimalField(_('Value'), max_digits=14, decimal_places=2)
    measured_at = models.DateField(_('Measured At'))
    status = models.CharField(_('Status'), max_length=10, choices=KeyRiskIndicator.STATUS_CHOICES, default='no_data')
    notes = models.TextField(_('Notes'), blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kri_measurements',
        verbose_name=_('Recorded By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('KRI Measurement')
        verbose_name_plural = _('KRI Measurements')
        ordering = ['-measured_at', '-created_at']
        unique_together = ['kri', 'measured_at']

    def __str__(self):
        return f"{self.kri.kri_id} = {self.value} ({self.measured_at})"

    def save(self, *args, **kwargs):
        self.status = self.kri.status_for(self.value)
        super().save(*args, **kwargs)
        latest = self.kri.measurements.order_by('-measured_at', '-created_at').first()
        if latest and latest.pk == self.pk:
            KeyRiskIndicator.objects.filter(pk=self.kri_id).update(
                current_value=self.value, current_status=self.status, last_measured_at=self.measured_at)
