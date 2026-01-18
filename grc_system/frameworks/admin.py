from django.contrib import admin
from .models import FrameworkTemplate, ControlMapping, RegulatoryRequirement


@admin.register(FrameworkTemplate)
class FrameworkTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'version', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(ControlMapping)
class ControlMappingAdmin(admin.ModelAdmin):
    list_display = ['source_framework', 'source_control_id', 'target_framework', 'target_control_id', 'mapping_type']
    list_filter = ['source_framework', 'target_framework', 'mapping_type']


@admin.register(RegulatoryRequirement)
class RegulatoryRequirementAdmin(admin.ModelAdmin):
    list_display = ['framework_code', 'requirement_id', 'title', 'requirement_type']
    list_filter = ['framework_code', 'requirement_type']
    search_fields = ['title', 'title_ar', 'requirement_id']
