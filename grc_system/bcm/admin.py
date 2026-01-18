from django.contrib import admin
from .models import (
    BusinessFunction, BusinessImpactAnalysis, BCPlan, DisasterRecoveryPlan,
    CrisisManagementTeam, CrisisTeamMember, CallTree, CallTreeNode,
    CrisisIncident, BCMTest, BCMTestFinding
)


@admin.register(BusinessFunction)
class BusinessFunctionAdmin(admin.ModelAdmin):
    list_display = ['function_id', 'name', 'criticality', 'status', 'department', 'owner']
    list_filter = ['criticality', 'status', 'organization']
    search_fields = ['name', 'name_ar', 'function_id']


@admin.register(BusinessImpactAnalysis)
class BusinessImpactAnalysisAdmin(admin.ModelAdmin):
    list_display = ['business_function', 'status', 'rto_hours', 'rpo_hours', 'assessment_date', 'assessor']
    list_filter = ['status', 'assessment_date']


@admin.register(BCPlan)
class BCPlanAdmin(admin.ModelAdmin):
    list_display = ['plan_id', 'title', 'status', 'version', 'owner', 'effective_date', 'last_tested_date']
    list_filter = ['status', 'organization']
    search_fields = ['title', 'title_ar', 'plan_id']


@admin.register(DisasterRecoveryPlan)
class DisasterRecoveryPlanAdmin(admin.ModelAdmin):
    list_display = ['plan_id', 'title', 'status', 'version', 'owner', 'effective_date']
    list_filter = ['status', 'organization']
    search_fields = ['title', 'title_ar', 'plan_id']


@admin.register(CrisisManagementTeam)
class CrisisManagementTeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'is_active']
    list_filter = ['is_active', 'organization']


@admin.register(CrisisTeamMember)
class CrisisTeamMemberAdmin(admin.ModelAdmin):
    list_display = ['team', 'user', 'role', 'is_primary', 'primary_phone']
    list_filter = ['role', 'is_primary', 'team']


@admin.register(CallTree)
class CallTreeAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'root_caller', 'is_active', 'last_tested']
    list_filter = ['is_active', 'organization']


@admin.register(CrisisIncident)
class CrisisIncidentAdmin(admin.ModelAdmin):
    list_display = ['incident_id', 'title', 'incident_type', 'severity', 'status', 'reported_at']
    list_filter = ['incident_type', 'severity', 'status', 'organization']
    search_fields = ['title', 'title_ar', 'incident_id']
    date_hierarchy = 'reported_at'


@admin.register(BCMTest)
class BCMTestAdmin(admin.ModelAdmin):
    list_display = ['test_id', 'title', 'test_type', 'status', 'scheduled_date', 'coordinator']
    list_filter = ['test_type', 'status', 'organization']
    search_fields = ['title', 'title_ar', 'test_id']


@admin.register(BCMTestFinding)
class BCMTestFindingAdmin(admin.ModelAdmin):
    list_display = ['test', 'title', 'severity', 'status', 'assigned_to', 'due_date']
    list_filter = ['severity', 'status']
