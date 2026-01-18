"""
Dashboard app serializers.
"""
from rest_framework import serializers
from .models import (
    DashboardWidget, Dashboard, DashboardWidgetPosition,
    ReportTemplate, GeneratedReport, KPI, KPIValue
)


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class DashboardWidgetPositionSerializer(serializers.ModelSerializer):
    widget = DashboardWidgetSerializer(read_only=True)
    
    class Meta:
        model = DashboardWidgetPosition
        fields = '__all__'


class DashboardSerializer(serializers.ModelSerializer):
    widget_positions = DashboardWidgetPositionSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Dashboard
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class DashboardListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ['id', 'name', 'name_ar', 'dashboard_type', 'is_default', 'is_public']


class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class GeneratedReportSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = GeneratedReport
        fields = '__all__'
        read_only_fields = ['created_at']


class GeneratedReportListSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = GeneratedReport
        fields = ['id', 'title', 'title_ar', 'template_name', 'status', 
                  'generated_at', 'file']


class KPISerializer(serializers.ModelSerializer):
    class Meta:
        model = KPI
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class KPIValueSerializer(serializers.ModelSerializer):
    kpi_name = serializers.CharField(source='kpi.name', read_only=True)
    
    class Meta:
        model = KPIValue
        fields = '__all__'
        read_only_fields = ['calculated_at']
