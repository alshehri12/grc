"""
BCM (Business Continuity Management) models for the GRC system.
BIA, BCP, DRP, Crisis Management, and Testing.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class BusinessFunction(models.Model):
    """
    وظيفة الأعمال - Business function for BIA
    """
    CRITICALITY_CHOICES = [
        ('critical', _('Critical')),
        ('essential', _('Essential')),
        ('necessary', _('Necessary')),
        ('desirable', _('Desirable')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('under_review', _('Under Review')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='business_functions',
        verbose_name=_('Organization')
    )
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='business_functions',
        verbose_name=_('Department')
    )
    
    # Identification
    function_id = models.CharField(_('Function ID'), max_length=50)
    name = models.CharField(_('Function Name'), max_length=300)
    name_ar = models.CharField(_('اسم الوظيفة'), max_length=300, blank=True)
    description = models.TextField(_('Description'))
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    criticality = models.CharField(_('Criticality'), max_length=20, choices=CRITICALITY_CHOICES, default='necessary')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_functions',
        verbose_name=_('Function Owner')
    )
    
    # Dependencies
    parent_function = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sub_functions',
        verbose_name=_('Parent Function')
    )
    dependent_functions = models.ManyToManyField(
        'self', 
        blank=True,
        symmetrical=False,
        related_name='dependencies',
        verbose_name=_('Dependent Functions')
    )
    
    # Related assets and systems
    related_assets = models.ManyToManyField(
        'risk.Asset', 
        blank=True,
        related_name='business_functions',
        verbose_name=_('Related Assets')
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_functions',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Business Function')
        verbose_name_plural = _('Business Functions')
        ordering = ['criticality', 'name']
        unique_together = ['organization', 'function_id']
    
    def __str__(self):
        return f"{self.function_id}: {self.name}"


class BusinessImpactAnalysis(models.Model):
    """
    تحليل أثر الأعمال - Business Impact Analysis (BIA)
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
        related_name='bias',
        verbose_name=_('Organization')
    )
    business_function = models.ForeignKey(
        BusinessFunction, 
        on_delete=models.CASCADE,
        related_name='bias',
        verbose_name=_('Business Function')
    )
    
    # Assessment details
    assessment_date = models.DateField(_('Assessment Date'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Recovery objectives
    rto_hours = models.PositiveIntegerField(
        _('RTO (Hours)'), 
        help_text=_('هدف وقت الاستعادة - Recovery Time Objective')
    )
    rpo_hours = models.PositiveIntegerField(
        _('RPO (Hours)'), 
        help_text=_('هدف نقطة الاستعادة - Recovery Point Objective')
    )
    mtpd_hours = models.PositiveIntegerField(
        _('MTPD (Hours)'), 
        help_text=_('أقصى فترة توقف مقبولة - Maximum Tolerable Period of Disruption')
    )
    
    # Impact assessment by time period
    impact_1_hour = models.PositiveIntegerField(_('Impact (1 Hour)'), default=1, help_text=_('1-5 scale'))
    impact_4_hours = models.PositiveIntegerField(_('Impact (4 Hours)'), default=2, help_text=_('1-5 scale'))
    impact_8_hours = models.PositiveIntegerField(_('Impact (8 Hours)'), default=3, help_text=_('1-5 scale'))
    impact_24_hours = models.PositiveIntegerField(_('Impact (24 Hours)'), default=4, help_text=_('1-5 scale'))
    impact_72_hours = models.PositiveIntegerField(_('Impact (72 Hours)'), default=5, help_text=_('1-5 scale'))
    
    # Financial impact
    financial_impact_daily = models.DecimalField(
        _('Financial Impact (Daily SAR)'), 
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Operational impact description
    operational_impact = models.TextField(_('Operational Impact'))
    operational_impact_ar = models.TextField(_('الأثر التشغيلي'), blank=True)
    
    # Reputational impact
    reputational_impact = models.TextField(_('Reputational Impact'), blank=True)
    reputational_impact_ar = models.TextField(_('الأثر السمعي'), blank=True)
    
    # Regulatory/Legal impact
    regulatory_impact = models.TextField(_('Regulatory/Legal Impact'), blank=True)
    regulatory_impact_ar = models.TextField(_('الأثر التنظيمي/القانوني'), blank=True)
    
    # Dependencies
    staff_dependencies = models.TextField(_('Staff Dependencies'), blank=True)
    staff_dependencies_ar = models.TextField(_('الاعتمادية على الموظفين'), blank=True)
    system_dependencies = models.TextField(_('System/IT Dependencies'), blank=True)
    system_dependencies_ar = models.TextField(_('الاعتمادية على الأنظمة'), blank=True)
    vendor_dependencies = models.TextField(_('Vendor/Third-party Dependencies'), blank=True)
    vendor_dependencies_ar = models.TextField(_('الاعتمادية على الموردين'), blank=True)
    
    # Minimum resources required
    minimum_staff = models.PositiveIntegerField(_('Minimum Staff Required'), default=1)
    minimum_equipment = models.TextField(_('Minimum Equipment'), blank=True)
    minimum_equipment_ar = models.TextField(_('الحد الأدنى من المعدات'), blank=True)
    
    # Peak periods
    peak_periods = models.TextField(_('Peak/Critical Periods'), blank=True)
    peak_periods_ar = models.TextField(_('فترات الذروة'), blank=True)
    
    # Assessor
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='conducted_bias',
        verbose_name=_('Assessor')
    )
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_bias',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Business Impact Analysis')
        verbose_name_plural = _('Business Impact Analyses')
        ordering = ['-assessment_date']
    
    def __str__(self):
        return f"BIA: {self.business_function.name} ({self.assessment_date})"


class BCPlan(models.Model):
    """
    خطة استمرارية الأعمال - Business Continuity Plan
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending_review', _('Pending Review')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('active', _('Active')),
        ('under_revision', _('Under Revision')),
        ('retired', _('Retired')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='bc_plans',
        verbose_name=_('Organization')
    )
    
    # Identification
    plan_id = models.CharField(_('Plan ID'), max_length=50)
    title = models.CharField(_('Plan Title'), max_length=300)
    title_ar = models.CharField(_('عنوان الخطة'), max_length=300, blank=True)
    
    version = models.CharField(_('Version'), max_length=20, default='1.0')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Scope
    scope = models.TextField(_('Plan Scope'), blank=True)
    scope_ar = models.TextField(_('نطاق الخطة'), blank=True)
    
    # Covered functions
    covered_functions = models.ManyToManyField(
        BusinessFunction, 
        related_name='bc_plans',
        verbose_name=_('Covered Functions')
    )
    
    # Plan content sections
    objectives = models.TextField(_('Objectives'), blank=True)
    objectives_ar = models.TextField(_('الأهداف'), blank=True)
    
    activation_criteria = models.TextField(_('Activation Criteria'), blank=True)
    activation_criteria_ar = models.TextField(_('معايير التفعيل'), blank=True)
    
    recovery_strategies = models.TextField(_('Recovery Strategies'), blank=True)
    recovery_strategies_ar = models.TextField(_('استراتيجيات الاستعادة'), blank=True)
    
    roles_responsibilities = models.TextField(_('Roles and Responsibilities'), blank=True)
    roles_responsibilities_ar = models.TextField(_('الأدوار والمسؤوليات'), blank=True)
    
    communication_plan = models.TextField(_('Communication Plan'), blank=True)
    communication_plan_ar = models.TextField(_('خطة الاتصالات'), blank=True)
    
    resource_requirements = models.TextField(_('Resource Requirements'), blank=True)
    resource_requirements_ar = models.TextField(_('متطلبات الموارد'), blank=True)
    
    alternate_site = models.TextField(_('Alternate Site Information'), blank=True)
    alternate_site_ar = models.TextField(_('معلومات الموقع البديل'), blank=True)
    
    # Document
    document = models.FileField(_('Plan Document'), upload_to='bcm/plans/', blank=True, null=True)
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_bc_plans',
        verbose_name=_('Plan Owner')
    )
    
    # Dates
    effective_date = models.DateField(_('Effective Date'), null=True, blank=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    last_tested_date = models.DateField(_('Last Tested Date'), null=True, blank=True)
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_bc_plans',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_bc_plans',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Business Continuity Plan')
        verbose_name_plural = _('Business Continuity Plans')
        ordering = ['-updated_at']
        unique_together = ['organization', 'plan_id']
    
    def __str__(self):
        return f"{self.plan_id}: {self.title}"


class DisasterRecoveryPlan(models.Model):
    """
    خطة التعافي من الكوارث - Disaster Recovery Plan
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('active', _('Active')),
        ('under_revision', _('Under Revision')),
        ('retired', _('Retired')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='dr_plans',
        verbose_name=_('Organization')
    )
    
    # Related BCP
    bc_plan = models.ForeignKey(
        BCPlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='dr_plans',
        verbose_name=_('Related BCP')
    )
    
    # Identification
    plan_id = models.CharField(_('Plan ID'), max_length=50)
    title = models.CharField(_('Plan Title'), max_length=300)
    title_ar = models.CharField(_('عنوان الخطة'), max_length=300, blank=True)
    
    version = models.CharField(_('Version'), max_length=20, default='1.0')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Scope
    scope = models.TextField(_('Plan Scope'), blank=True)
    scope_ar = models.TextField(_('نطاق الخطة'), blank=True)
    
    # Systems covered
    covered_systems = models.TextField(_('Covered Systems'), blank=True)
    covered_systems_ar = models.TextField(_('الأنظمة المشمولة'), blank=True)
    
    # Recovery procedures
    recovery_procedures = models.TextField(_('Recovery Procedures'), blank=True)
    recovery_procedures_ar = models.TextField(_('إجراءات الاستعادة'), blank=True)
    
    # Backup information
    backup_strategy = models.TextField(_('Backup Strategy'), blank=True)
    backup_strategy_ar = models.TextField(_('استراتيجية النسخ الاحتياطي'), blank=True)
    backup_location = models.CharField(_('Backup Location'), max_length=300, blank=True)
    backup_frequency = models.CharField(_('Backup Frequency'), max_length=100, blank=True)
    
    # DR site
    dr_site_location = models.TextField(_('DR Site Location'), blank=True)
    dr_site_location_ar = models.TextField(_('موقع التعافي'), blank=True)
    
    # Vendor information
    vendor_contacts = models.TextField(_('Vendor Contacts'), blank=True)
    
    # Document
    document = models.FileField(_('Plan Document'), upload_to='bcm/dr_plans/', blank=True, null=True)
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_dr_plans',
        verbose_name=_('Plan Owner')
    )
    
    # Dates
    effective_date = models.DateField(_('Effective Date'), null=True, blank=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    last_tested_date = models.DateField(_('Last Tested Date'), null=True, blank=True)
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_dr_plans',
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(_('Approved Date'), null=True, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_dr_plans',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Disaster Recovery Plan')
        verbose_name_plural = _('Disaster Recovery Plans')
        ordering = ['-updated_at']
        unique_together = ['organization', 'plan_id']
    
    def __str__(self):
        return f"{self.plan_id}: {self.title}"


class CrisisManagementTeam(models.Model):
    """
    فريق إدارة الأزمات - Crisis Management Team
    """
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='crisis_teams',
        verbose_name=_('Organization')
    )
    
    name = models.CharField(_('Team Name'), max_length=200)
    name_ar = models.CharField(_('اسم الفريق'), max_length=200, blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Crisis Management Team')
        verbose_name_plural = _('Crisis Management Teams')
    
    def __str__(self):
        return self.name


class CrisisTeamMember(models.Model):
    """
    عضو فريق الأزمات - Crisis team member
    """
    ROLE_CHOICES = [
        ('commander', _('Incident Commander')),
        ('deputy', _('Deputy Commander')),
        ('operations', _('Operations Lead')),
        ('communications', _('Communications Lead')),
        ('logistics', _('Logistics Lead')),
        ('hr', _('HR Lead')),
        ('it', _('IT Lead')),
        ('finance', _('Finance Lead')),
        ('member', _('Team Member')),
    ]
    
    team = models.ForeignKey(
        CrisisManagementTeam, 
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_('Team')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='crisis_team_roles',
        verbose_name=_('User')
    )
    
    role = models.CharField(_('Role'), max_length=20, choices=ROLE_CHOICES, default='member')
    role_description = models.TextField(_('Role Description'), blank=True)
    role_description_ar = models.TextField(_('وصف الدور'), blank=True)
    
    # Contact information (for emergencies)
    primary_phone = models.CharField(_('Primary Phone'), max_length=20)
    secondary_phone = models.CharField(_('Secondary Phone'), max_length=20, blank=True)
    personal_email = models.EmailField(_('Personal Email'), blank=True)
    
    is_primary = models.BooleanField(_('Primary Contact'), default=True)
    backup_member = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='backup_for',
        verbose_name=_('Backup Member')
    )
    
    class Meta:
        verbose_name = _('Crisis Team Member')
        verbose_name_plural = _('Crisis Team Members')
        unique_together = ['team', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


class CallTree(models.Model):
    """
    شجرة الاتصال - Communication call tree
    """
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='call_trees',
        verbose_name=_('Organization')
    )
    
    name = models.CharField(_('Call Tree Name'), max_length=200)
    name_ar = models.CharField(_('اسم شجرة الاتصال'), max_length=200, blank=True)
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Root caller
    root_caller = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='root_call_trees',
        verbose_name=_('Root Caller')
    )
    
    is_active = models.BooleanField(_('Active'), default=True)
    last_tested = models.DateTimeField(_('Last Tested'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Call Tree')
        verbose_name_plural = _('Call Trees')
    
    def __str__(self):
        return self.name


class CallTreeNode(models.Model):
    """
    عقدة شجرة الاتصال - Node in call tree
    """
    call_tree = models.ForeignKey(
        CallTree, 
        on_delete=models.CASCADE,
        related_name='nodes',
        verbose_name=_('Call Tree')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='call_tree_nodes',
        verbose_name=_('User')
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='children',
        verbose_name=_('Parent Node')
    )
    
    order = models.PositiveIntegerField(_('Call Order'), default=1)
    phone = models.CharField(_('Phone'), max_length=20)
    alternate_phone = models.CharField(_('Alternate Phone'), max_length=20, blank=True)
    
    class Meta:
        verbose_name = _('Call Tree Node')
        verbose_name_plural = _('Call Tree Nodes')
        ordering = ['call_tree', 'order']
    
    def __str__(self):
        return f"{self.user.get_full_name()} (Order: {self.order})"


class CrisisIncident(models.Model):
    """
    حادثة أزمة - Crisis incident record
    """
    SEVERITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('reported', _('Reported')),
        ('assessing', _('Assessing')),
        ('responding', _('Responding')),
        ('recovering', _('Recovering')),
        ('resolved', _('Resolved')),
        ('closed', _('Closed')),
    ]
    
    INCIDENT_TYPES = [
        ('natural_disaster', _('Natural Disaster')),
        ('cyber_attack', _('Cyber Attack')),
        ('infrastructure', _('Infrastructure Failure')),
        ('pandemic', _('Pandemic')),
        ('security', _('Security Incident')),
        ('operational', _('Operational Disruption')),
        ('other', _('Other')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='crisis_incidents',
        verbose_name=_('Organization')
    )
    
    # Identification
    incident_id = models.CharField(_('Incident ID'), max_length=50)
    title = models.CharField(_('Incident Title'), max_length=300)
    title_ar = models.CharField(_('عنوان الحادثة'), max_length=300, blank=True)
    
    incident_type = models.CharField(_('Incident Type'), max_length=20, choices=INCIDENT_TYPES)
    severity = models.CharField(_('Severity'), max_length=20, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='reported')
    
    # Description
    description = models.TextField(_('Description'))
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Impact
    impact_description = models.TextField(_('Impact Description'))
    impact_description_ar = models.TextField(_('وصف الأثر'), blank=True)
    affected_functions = models.ManyToManyField(
        BusinessFunction, 
        blank=True,
        related_name='crisis_incidents',
        verbose_name=_('Affected Functions')
    )
    
    # Response
    response_actions = models.TextField(_('Response Actions'), blank=True)
    response_actions_ar = models.TextField(_('إجراءات الاستجابة'), blank=True)
    
    # Team assignment
    crisis_team = models.ForeignKey(
        CrisisManagementTeam, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='incidents',
        verbose_name=_('Assigned Crisis Team')
    )
    incident_commander = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='commanded_incidents',
        verbose_name=_('Incident Commander')
    )
    
    # Plans activated
    activated_bc_plan = models.ForeignKey(
        BCPlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='incidents',
        verbose_name=_('Activated BCP')
    )
    activated_dr_plan = models.ForeignKey(
        DisasterRecoveryPlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='incidents',
        verbose_name=_('Activated DRP')
    )
    
    # Timeline
    reported_at = models.DateTimeField(_('Reported At'))
    declared_at = models.DateTimeField(_('Crisis Declared At'), null=True, blank=True)
    resolved_at = models.DateTimeField(_('Resolved At'), null=True, blank=True)
    closed_at = models.DateTimeField(_('Closed At'), null=True, blank=True)
    
    # Lessons learned
    lessons_learned = models.TextField(_('Lessons Learned'), blank=True)
    lessons_learned_ar = models.TextField(_('الدروس المستفادة'), blank=True)
    
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='reported_incidents',
        verbose_name=_('Reported By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Crisis Incident')
        verbose_name_plural = _('Crisis Incidents')
        ordering = ['-reported_at']
        unique_together = ['organization', 'incident_id']
    
    def __str__(self):
        return f"{self.incident_id}: {self.title}"


class BCMTest(models.Model):
    """
    اختبار استمرارية الأعمال - BCM Test/Exercise
    """
    TEST_TYPES = [
        ('tabletop', _('Tabletop Exercise')),
        ('walkthrough', _('Walkthrough')),
        ('simulation', _('Simulation')),
        ('parallel', _('Parallel Test')),
        ('full', _('Full Interruption Test')),
    ]
    
    STATUS_CHOICES = [
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='bcm_tests',
        verbose_name=_('Organization')
    )
    
    # Identification
    test_id = models.CharField(_('Test ID'), max_length=50)
    title = models.CharField(_('Test Title'), max_length=300)
    title_ar = models.CharField(_('عنوان الاختبار'), max_length=300, blank=True)
    
    test_type = models.CharField(_('Test Type'), max_length=20, choices=TEST_TYPES, default='tabletop')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Scope
    objectives = models.TextField(_('Test Objectives'), blank=True)
    objectives_ar = models.TextField(_('أهداف الاختبار'), blank=True)
    scope = models.TextField(_('Test Scope'), blank=True)
    scope_ar = models.TextField(_('نطاق الاختبار'), blank=True)
    
    # Plans being tested
    bc_plan = models.ForeignKey(
        BCPlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tests',
        verbose_name=_('BCP Being Tested')
    )
    dr_plan = models.ForeignKey(
        DisasterRecoveryPlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tests',
        verbose_name=_('DRP Being Tested')
    )
    
    # Scenario
    scenario = models.TextField(_('Test Scenario'))
    scenario_ar = models.TextField(_('سيناريو الاختبار'), blank=True)
    
    # Schedule
    scheduled_date = models.DateField(_('Scheduled Date'))
    scheduled_duration_hours = models.PositiveIntegerField(_('Scheduled Duration (Hours)'), default=2)
    actual_start = models.DateTimeField(_('Actual Start'), null=True, blank=True)
    actual_end = models.DateTimeField(_('Actual End'), null=True, blank=True)
    
    # Participants
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True,
        related_name='bcm_test_participations',
        verbose_name=_('Participants')
    )
    
    # Coordinator
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='coordinated_tests',
        verbose_name=_('Test Coordinator')
    )
    
    # Results
    overall_result = models.CharField(_('Overall Result'), max_length=20, blank=True)
    results_summary = models.TextField(_('Results Summary'), blank=True)
    results_summary_ar = models.TextField(_('ملخص النتائج'), blank=True)
    
    strengths_identified = models.TextField(_('Strengths Identified'), blank=True)
    strengths_identified_ar = models.TextField(_('نقاط القوة'), blank=True)
    weaknesses_identified = models.TextField(_('Weaknesses Identified'), blank=True)
    weaknesses_identified_ar = models.TextField(_('نقاط الضعف'), blank=True)
    
    lessons_learned = models.TextField(_('Lessons Learned'), blank=True)
    lessons_learned_ar = models.TextField(_('الدروس المستفادة'), blank=True)
    
    # Report document
    report_document = models.FileField(_('Test Report'), upload_to='bcm/test_reports/', blank=True, null=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_bcm_tests',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('BCM Test')
        verbose_name_plural = _('BCM Tests')
        ordering = ['-scheduled_date']
        unique_together = ['organization', 'test_id']
    
    def __str__(self):
        return f"{self.test_id}: {self.title}"


class BCMTestFinding(models.Model):
    """
    نتيجة اختبار - BCM Test finding
    """
    SEVERITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('open', _('Open')),
        ('in_progress', _('In Progress')),
        ('resolved', _('Resolved')),
        ('accepted', _('Accepted')),
    ]
    
    test = models.ForeignKey(
        BCMTest, 
        on_delete=models.CASCADE,
        related_name='findings',
        verbose_name=_('Test')
    )
    
    title = models.CharField(_('Finding Title'), max_length=300)
    title_ar = models.CharField(_('عنوان النتيجة'), max_length=300, blank=True)
    description = models.TextField(_('Finding Description'))
    description_ar = models.TextField(_('وصف النتيجة'), blank=True)
    
    severity = models.CharField(_('Severity'), max_length=20, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='open')
    
    recommendation = models.TextField(_('Recommendation'))
    recommendation_ar = models.TextField(_('التوصية'), blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_bcm_findings',
        verbose_name=_('Assigned To')
    )
    due_date = models.DateField(_('Due Date'), null=True, blank=True)
    
    # Resolution
    resolution = models.TextField(_('Resolution'), blank=True)
    resolution_ar = models.TextField(_('الحل'), blank=True)
    resolved_date = models.DateField(_('Resolved Date'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('BCM Test Finding')
        verbose_name_plural = _('BCM Test Findings')
        ordering = ['-severity', '-created_at']
    
    def __str__(self):
        return f"{self.test.test_id}: {self.title}"
