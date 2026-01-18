"""
Compliance app serializers.
"""
from rest_framework import serializers
from .models import (
    ControlFramework, ControlDomain, Control, ControlImplementation,
    Audit, AuditFinding, CorrectiveAction, Evidence, GapAssessment
)


class ControlFrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlFramework
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ControlDomainSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    
    class Meta:
        model = ControlDomain
        fields = '__all__'


class ControlSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    framework_code = serializers.CharField(source='domain.framework.code', read_only=True)
    
    class Meta:
        model = Control
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'domain': {'required': False, 'allow_null': True},
            'parent_control': {'required': False, 'allow_null': True},
        }


class ControlListSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    framework_code = serializers.CharField(source='domain.framework.code', read_only=True)
    
    class Meta:
        model = Control
        fields = ['id', 'control_id', 'title', 'title_ar', 'control_type', 
                  'domain_name', 'framework_code']


class ControlImplementationSerializer(serializers.ModelSerializer):
    control_title = serializers.CharField(source='control.title', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    maturity_display = serializers.CharField(source='get_maturity_level_display', read_only=True)
    
    class Meta:
        model = ControlImplementation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class AuditSerializer(serializers.ModelSerializer):
    lead_auditor_name = serializers.CharField(source='lead_auditor.get_full_name', read_only=True)
    
    class Meta:
        model = Audit
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'lead_auditor': {'required': False, 'allow_null': True},
            'created_by': {'required': False, 'allow_null': True},
            'framework': {'required': False, 'allow_null': True},
        }


class AuditListSerializer(serializers.ModelSerializer):
    lead_auditor_name = serializers.CharField(source='lead_auditor.get_full_name', read_only=True)
    
    class Meta:
        model = Audit
        fields = ['id', 'audit_id', 'title', 'title_ar', 'audit_type', 'status',
                  'lead_auditor_name', 'planned_start_date', 'planned_end_date']


class AuditFindingSerializer(serializers.ModelSerializer):
    audit_title = serializers.CharField(source='audit.title', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = AuditFinding
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class AuditFindingListSerializer(serializers.ModelSerializer):
    audit_title = serializers.CharField(source='audit.title', read_only=True)
    
    class Meta:
        model = AuditFinding
        fields = ['id', 'finding_id', 'title', 'title_ar', 'finding_type', 
                  'status', 'audit_title', 'due_date']


class CorrectiveActionSerializer(serializers.ModelSerializer):
    finding_title = serializers.CharField(source='finding.title', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = CorrectiveAction
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class EvidenceSerializer(serializers.ModelSerializer):
    control_title = serializers.CharField(source='control_implementation.control.title', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Evidence
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class EvidenceListSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Evidence
        fields = ['id', 'evidence_id', 'title', 'title_ar', 'evidence_type',
                  'status', 'collection_date', 'valid_until', 'is_expired']


class GapAssessmentSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    assessor_name = serializers.CharField(source='assessor.get_full_name', read_only=True)
    
    class Meta:
        model = GapAssessment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class GapAssessmentListSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    
    class Meta:
        model = GapAssessment
        fields = ['id', 'assessment_id', 'title', 'title_ar', 'framework_name',
                  'status', 'assessment_date', 'compliance_score', 'maturity_score']
