"""
Governance app serializers.
"""
from rest_framework import serializers
from .models import PolicyCategory, Policy, PolicyVersion, PolicyAcknowledgment, Procedure, Document


class PolicyCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyCategory
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class PolicySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Policy
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'category': {'required': False, 'allow_null': True},
            'owner': {'required': False, 'allow_null': True},
            'department': {'required': False, 'allow_null': True},
            'approved_by': {'required': False, 'allow_null': True},
            'created_by': {'required': False, 'allow_null': True},
        }


class PolicyListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Policy
        fields = ['id', 'policy_id', 'title', 'title_ar', 'status', 'version', 
                  'category_name', 'owner_name', 'effective_date', 'review_date']


class PolicyVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = PolicyVersion
        fields = '__all__'
        read_only_fields = ['created_at']


class PolicyAcknowledgmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    
    class Meta:
        model = PolicyAcknowledgment
        fields = '__all__'
        read_only_fields = ['acknowledged_at']


class ProcedureSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Procedure
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ProcedureListSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Procedure
        fields = ['id', 'procedure_id', 'title', 'title_ar', 'status', 'version',
                  'policy_title', 'owner_name', 'effective_date', 'review_date']


class DocumentSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class DocumentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'document_id', 'title', 'title_ar', 'document_type', 
                  'status', 'classification', 'effective_date']
