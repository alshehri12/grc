from django.contrib import admin
from .models import (
    DashboardWidget, Dashboard, DashboardWidgetPosition,
    ReportTemplate, GeneratedReport, KPI, KPIValue
)


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'data_source', 'is_active']
    list_filter = ['widget_type', 'data_source', 'is_active']
    search_fields = ['name', 'name_ar']


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'dashboard_type', 'is_default', 'is_public', 'owner']
    list_filter = ['dashboard_type', 'is_default', 'is_public']
    search_fields = ['name', 'name_ar']


@admin.register(DashboardWidgetPosition)
class DashboardWidgetPositionAdmin(admin.ModelAdmin):
    list_display = ['dashboard', 'widget', 'row', 'column']
    list_filter = ['dashboard']


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'report_type', 'output_format', 'is_active']
    list_filter = ['report_type', 'output_format', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'template', 'status', 'generated_by', 'generated_at']
    list_filter = ['status', 'template', 'organization']
    search_fields = ['title', 'title_ar']
    date_hierarchy = 'created_at'


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'target_value', 'unit', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(KPIValue)
class KPIValueAdmin(admin.ModelAdmin):
    list_display = ['organization', 'kpi', 'value', 'period_date']
    list_filter = ['kpi', 'organization']
    date_hierarchy = 'period_date'
