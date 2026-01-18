from django.contrib import admin
from .models import PolicyCategory, Policy, PolicyVersion, PolicyAcknowledgment, Procedure, Document


@admin.register(PolicyCategory)
class PolicyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_id', 'title', 'status', 'version', 'owner', 'effective_date', 'review_date']
    list_filter = ['status', 'classification', 'category', 'organization']
    search_fields = ['title', 'title_ar', 'policy_id']
    raw_id_fields = ['owner', 'approved_by', 'created_by']
    date_hierarchy = 'created_at'


@admin.register(PolicyVersion)
class PolicyVersionAdmin(admin.ModelAdmin):
    list_display = ['policy', 'version', 'created_by', 'created_at']
    list_filter = ['created_at']


@admin.register(PolicyAcknowledgment)
class PolicyAcknowledgmentAdmin(admin.ModelAdmin):
    list_display = ['policy', 'user', 'version', 'acknowledged_at']
    list_filter = ['acknowledged_at']
    raw_id_fields = ['policy', 'user']


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ['procedure_id', 'title', 'status', 'version', 'owner', 'effective_date']
    list_filter = ['status', 'organization']
    search_fields = ['title', 'title_ar', 'procedure_id']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['document_id', 'title', 'document_type', 'status', 'classification', 'owner']
    list_filter = ['document_type', 'status', 'classification', 'organization']
    search_fields = ['title', 'title_ar', 'document_id']
