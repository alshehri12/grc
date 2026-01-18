"""
Risk app serializers.
"""
from rest_framework import serializers
from .models import AssetCategory, Asset, RiskCategory, Risk, RiskAssessment, RiskTreatment, RiskAcceptance


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = '__all__'
        read_only_fields = ['created_at']


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    asset_value = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Asset
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class AssetListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Asset
        fields = ['id', 'asset_id', 'name', 'name_ar', 'category_name', 'criticality', 'status', 'owner_name']


class RiskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCategory
        fields = '__all__'
        read_only_fields = ['created_at']


class RiskSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    inherent_risk_score = serializers.IntegerField(read_only=True)
    residual_risk_score = serializers.IntegerField(read_only=True)
    risk_level = serializers.CharField(read_only=True)
    
    class Meta:
        model = Risk
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'identified_date']
        extra_kwargs = {
            'category': {'required': False, 'allow_null': True},
            'owner': {'required': False, 'allow_null': True},
            'department': {'required': False, 'allow_null': True},
        }


class RiskListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    inherent_risk_score = serializers.IntegerField(read_only=True)
    risk_level = serializers.CharField(read_only=True)
    
    class Meta:
        model = Risk
        fields = ['id', 'risk_id', 'title', 'title_ar', 'risk_type', 'status', 'category_name',
                  'owner_name', 'inherent_likelihood', 'inherent_impact', 'inherent_risk_score',
                  'risk_level', 'identified_date']


class RiskAssessmentSerializer(serializers.ModelSerializer):
    risk_title = serializers.CharField(source='risk.title', read_only=True)
    assessor_name = serializers.CharField(source='assessor.get_full_name', read_only=True)
    risk_score = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = RiskAssessment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class RiskTreatmentSerializer(serializers.ModelSerializer):
    risk_title = serializers.CharField(source='risk.title', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = RiskTreatment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class RiskAcceptanceSerializer(serializers.ModelSerializer):
    risk_title = serializers.CharField(source='risk.title', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    accepted_risk_score = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = RiskAcceptance
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'requested_date']
