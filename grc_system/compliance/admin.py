from django.contrib import admin
from .models import (
    ControlFramework, ControlDomain, Control, ControlImplementation,
    Audit, AuditFinding, CorrectiveAction, Evidence, GapAssessment
)


@admin.register(ControlFramework)
class ControlFrameworkAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'version', 'is_mandatory', 'is_active']
    list_filter = ['is_mandatory', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(ControlDomain)
class ControlDomainAdmin(admin.ModelAdmin):
    list_display = ['framework', 'code', 'name', 'order']
    list_filter = ['framework']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = ['control_id', 'title', 'control_type', 'domain']
    list_filter = ['control_type', 'domain__framework']
    search_fields = ['title', 'title_ar', 'control_id']


@admin.register(ControlImplementation)
class ControlImplementationAdmin(admin.ModelAdmin):
    list_display = ['organization', 'control', 'status', 'maturity_level', 'owner', 'last_tested_date']
    list_filter = ['status', 'maturity_level', 'organization', 'control__domain__framework']
    raw_id_fields = ['control', 'owner']


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ['audit_id', 'title', 'audit_type', 'status', 'lead_auditor', 'planned_start_date']
    list_filter = ['audit_type', 'status', 'organization']
    search_fields = ['title', 'title_ar', 'audit_id']
    date_hierarchy = 'planned_start_date'


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = ['finding_id', 'title', 'audit', 'finding_type', 'status', 'assigned_to', 'due_date']
    list_filter = ['finding_type', 'status', 'audit']
    search_fields = ['title', 'title_ar', 'finding_id']


@admin.register(CorrectiveAction)
class CorrectiveActionAdmin(admin.ModelAdmin):
    list_display = ['car_id', 'title', 'finding', 'status', 'priority', 'owner', 'target_date']
    list_filter = ['status', 'priority', 'organization']
    search_fields = ['title', 'title_ar', 'car_id']


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ['evidence_id', 'title', 'evidence_type', 'status', 'collection_date', 'valid_until']
    list_filter = ['evidence_type', 'status', 'organization']
    search_fields = ['title', 'title_ar', 'evidence_id']


@admin.register(GapAssessment)
class GapAssessmentAdmin(admin.ModelAdmin):
    list_display = ['assessment_id', 'title', 'framework', 'status', 'compliance_score', 'assessment_date']
    list_filter = ['status', 'framework', 'organization']
    search_fields = ['title', 'title_ar', 'assessment_id']
