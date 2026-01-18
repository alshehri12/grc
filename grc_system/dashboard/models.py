"""
Dashboard models for the GRC system.
KPIs, reports, charts, and executive summaries.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DashboardWidget(models.Model):
    """
    عنصر لوحة المعلومات - Dashboard widget configuration
    """
    WIDGET_TYPES = [
        ('kpi', _('KPI Card')),
        ('chart_bar', _('Bar Chart')),
        ('chart_line', _('Line Chart')),
        ('chart_pie', _('Pie Chart')),
        ('chart_doughnut', _('Doughnut Chart')),
        ('risk_matrix', _('Risk Matrix')),
        ('table', _('Data Table')),
        ('timeline', _('Timeline')),
        ('list', _('List')),
    ]
    
    DATA_SOURCES = [
        ('risks', _('Risks')),
        ('controls', _('Controls')),
        ('compliance', _('Compliance')),
        ('audits', _('Audits')),
        ('tasks', _('Tasks')),
        ('policies', _('Policies')),
        ('bcm', _('BCM')),
        ('custom', _('Custom Query')),
    ]
    
    name = models.CharField(_('Widget Name'), max_length=200)
    name_ar = models.CharField(_('اسم العنصر'), max_length=200, blank=True)
    
    widget_type = models.CharField(_('Widget Type'), max_length=20, choices=WIDGET_TYPES)
    data_source = models.CharField(_('Data Source'), max_length=20, choices=DATA_SOURCES)
    
    # Query configuration
    query_config = models.JSONField(_('Query Configuration'), default=dict, blank=True)
    
    # Display settings
    color = models.CharField(_('Color'), max_length=20, default='primary')
    icon = models.CharField(_('Icon'), max_length=50, blank=True)
    
    # Size
    width = models.PositiveIntegerField(_('Width (columns)'), default=3)
    height = models.PositiveIntegerField(_('Height'), default=1)
    
    # Refresh interval in seconds (0 = no auto-refresh)
    refresh_interval = models.PositiveIntegerField(_('Refresh Interval (seconds)'), default=0)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard Widget')
        verbose_name_plural = _('Dashboard Widgets')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Dashboard(models.Model):
    """
    لوحة المعلومات - Dashboard configuration
    """
    DASHBOARD_TYPES = [
        ('executive', _('Executive Dashboard')),
        ('operational', _('Operational Dashboard')),
        ('risk', _('Risk Dashboard')),
        ('compliance', _('Compliance Dashboard')),
        ('audit', _('Audit Dashboard')),
        ('bcm', _('BCM Dashboard')),
        ('custom', _('Custom Dashboard')),
    ]
    
    name = models.CharField(_('Dashboard Name'), max_length=200)
    name_ar = models.CharField(_('اسم لوحة المعلومات'), max_length=200, blank=True)
    
    dashboard_type = models.CharField(_('Dashboard Type'), max_length=20, choices=DASHBOARD_TYPES, default='custom')
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Widgets on this dashboard
    widgets = models.ManyToManyField(
        DashboardWidget, 
        through='DashboardWidgetPosition',
        related_name='dashboards',
        verbose_name=_('Widgets')
    )
    
    # Access control
    is_default = models.BooleanField(_('Default Dashboard'), default=False)
    is_public = models.BooleanField(_('Public'), default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='owned_dashboards',
        verbose_name=_('Owner')
    )
    allowed_roles = models.ManyToManyField(
        'core.Role', 
        blank=True,
        related_name='dashboards',
        verbose_name=_('Allowed Roles')
    )
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard')
        verbose_name_plural = _('Dashboards')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DashboardWidgetPosition(models.Model):
    """
    موقع العنصر - Widget position on dashboard
    """
    dashboard = models.ForeignKey(
        Dashboard, 
        on_delete=models.CASCADE,
        related_name='widget_positions',
        verbose_name=_('Dashboard')
    )
    widget = models.ForeignKey(
        DashboardWidget, 
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name=_('Widget')
    )
    
    # Grid position
    row = models.PositiveIntegerField(_('Row'), default=0)
    column = models.PositiveIntegerField(_('Column'), default=0)
    
    # Override default size
    width = models.PositiveIntegerField(_('Width'), null=True, blank=True)
    height = models.PositiveIntegerField(_('Height'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Dashboard Widget Position')
        verbose_name_plural = _('Dashboard Widget Positions')
        unique_together = ['dashboard', 'row', 'column']
    
    def __str__(self):
        return f"{self.dashboard.name} - {self.widget.name} ({self.row}, {self.column})"


class ReportTemplate(models.Model):
    """
    قالب التقرير - Report template
    """
    REPORT_TYPES = [
        ('compliance', _('Compliance Report')),
        ('risk', _('Risk Report')),
        ('audit', _('Audit Report')),
        ('executive', _('Executive Summary')),
        ('bcm', _('BCM Report')),
        ('gap', _('Gap Analysis Report')),
        ('custom', _('Custom Report')),
    ]
    
    OUTPUT_FORMATS = [
        ('pdf', _('PDF')),
        ('excel', _('Excel')),
        ('word', _('Word')),
        ('html', _('HTML')),
    ]
    
    name = models.CharField(_('Template Name'), max_length=200)
    name_ar = models.CharField(_('اسم القالب'), max_length=200, blank=True)
    code = models.CharField(_('Template Code'), max_length=50, unique=True)
    
    report_type = models.CharField(_('Report Type'), max_length=20, choices=REPORT_TYPES)
    output_format = models.CharField(_('Output Format'), max_length=10, choices=OUTPUT_FORMATS, default='pdf')
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Template configuration
    template_config = models.JSONField(_('Template Configuration'), default=dict)
    
    # Template file (for custom templates)
    template_file = models.FileField(_('Template File'), upload_to='report_templates/', blank=True, null=True)
    
    # Header/Footer customization
    include_logo = models.BooleanField(_('Include Logo'), default=True)
    include_header = models.BooleanField(_('Include Header'), default=True)
    include_footer = models.BooleanField(_('Include Footer'), default=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Report Template')
        verbose_name_plural = _('Report Templates')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class GeneratedReport(models.Model):
    """
    التقرير المولد - Generated report instance
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('generating', _('Generating')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='generated_reports',
        verbose_name=_('Organization')
    )
    template = models.ForeignKey(
        ReportTemplate, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='generated_reports',
        verbose_name=_('Template')
    )
    
    title = models.CharField(_('Report Title'), max_length=300)
    title_ar = models.CharField(_('عنوان التقرير'), max_length=300, blank=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Generation parameters
    parameters = models.JSONField(_('Report Parameters'), default=dict)
    
    # Date range
    date_from = models.DateField(_('From Date'), null=True, blank=True)
    date_to = models.DateField(_('To Date'), null=True, blank=True)
    
    # Generated file
    file = models.FileField(_('Report File'), upload_to='generated_reports/', blank=True, null=True)
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), null=True, blank=True)
    
    # Generation info
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='generated_reports',
        verbose_name=_('Generated By')
    )
    generated_at = models.DateTimeField(_('Generated At'), null=True, blank=True)
    generation_time_seconds = models.FloatField(_('Generation Time (seconds)'), null=True, blank=True)
    
    # Error info
    error_message = models.TextField(_('Error Message'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Generated Report')
        verbose_name_plural = _('Generated Reports')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.created_at.date()})"


class KPI(models.Model):
    """
    مؤشر الأداء - Key Performance Indicator
    """
    TREND_DIRECTIONS = [
        ('up_good', _('Up is Good')),
        ('down_good', _('Down is Good')),
        ('neutral', _('Neutral')),
    ]
    
    name = models.CharField(_('KPI Name'), max_length=200)
    name_ar = models.CharField(_('اسم المؤشر'), max_length=200, blank=True)
    code = models.CharField(_('KPI Code'), max_length=50, unique=True)
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Calculation
    calculation_query = models.TextField(_('Calculation Query'), blank=True)
    calculation_config = models.JSONField(_('Calculation Config'), default=dict)
    
    # Thresholds
    target_value = models.DecimalField(_('Target Value'), max_digits=10, decimal_places=2, null=True, blank=True)
    warning_threshold = models.DecimalField(_('Warning Threshold'), max_digits=10, decimal_places=2, null=True, blank=True)
    critical_threshold = models.DecimalField(_('Critical Threshold'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Display
    unit = models.CharField(_('Unit'), max_length=20, blank=True)
    trend_direction = models.CharField(_('Trend Direction'), max_length=20, choices=TREND_DIRECTIONS, default='up_good')
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('KPI')
        verbose_name_plural = _('KPIs')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class KPIValue(models.Model):
    """
    قيمة المؤشر - KPI historical value
    """
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE,
        related_name='kpi_values',
        verbose_name=_('Organization')
    )
    kpi = models.ForeignKey(
        KPI, 
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name=_('KPI')
    )
    
    value = models.DecimalField(_('Value'), max_digits=10, decimal_places=2)
    period_date = models.DateField(_('Period Date'))
    
    # Optional breakdown
    breakdown = models.JSONField(_('Breakdown'), default=dict, blank=True)
    
    calculated_at = models.DateTimeField(_('Calculated At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('KPI Value')
        verbose_name_plural = _('KPI Values')
        ordering = ['-period_date']
        unique_together = ['organization', 'kpi', 'period_date']
    
    def __str__(self):
        return f"{self.kpi.name}: {self.value} ({self.period_date})"
