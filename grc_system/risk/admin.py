from django.contrib import admin
from .models import AssetCategory, Asset, RiskCategory, Risk, RiskAssessment, RiskTreatment, RiskAcceptance


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['asset_id', 'name', 'category', 'criticality', 'status', 'owner']
    list_filter = ['criticality', 'status', 'category', 'organization']
    search_fields = ['name', 'name_ar', 'asset_id']


@admin.register(RiskCategory)
class RiskCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ['risk_id', 'title', 'risk_type', 'status', 'inherent_likelihood', 'inherent_impact', 'owner']
    list_filter = ['risk_type', 'status', 'category', 'organization']
    search_fields = ['title', 'title_ar', 'risk_id']
    raw_id_fields = ['owner', 'created_by']


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ['risk', 'assessment_type', 'status', 'assessment_date', 'assessor']
    list_filter = ['assessment_type', 'status', 'assessment_date']


@admin.register(RiskTreatment)
class RiskTreatmentAdmin(admin.ModelAdmin):
    list_display = ['risk', 'treatment_option', 'title', 'status', 'owner', 'due_date']
    list_filter = ['treatment_option', 'status']


@admin.register(RiskAcceptance)
class RiskAcceptanceAdmin(admin.ModelAdmin):
    list_display = ['risk', 'status', 'requested_by', 'approved_by', 'valid_until']
    list_filter = ['status']
