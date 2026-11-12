"""
Risk app serializers.
"""
from rest_framework import serializers
from .models import (
    AssetCategory, Asset, RiskCategory, Risk, RiskAssessment, RiskTreatment, RiskAcceptance,
    RiskAppetite, KeyRiskIndicator, KRIMeasurement,
)


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
    residual_risk_level = serializers.CharField(read_only=True)
    appetite_status = serializers.JSONField(read_only=True)
    
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
    residual_risk_score = serializers.IntegerField(read_only=True)
    risk_level = serializers.CharField(read_only=True)
    residual_risk_level = serializers.CharField(read_only=True)
    appetite = serializers.SerializerMethodField()
    
    class Meta:
        model = Risk
        fields = ['id', 'risk_id', 'title', 'title_ar', 'risk_type', 'status', 'category_name',
                  'owner_name', 'inherent_likelihood', 'inherent_impact', 'inherent_risk_score',
                  'residual_likelihood', 'residual_impact', 'residual_risk_score', 'residual_risk_level',
                  'risk_level', 'appetite', 'review_date', 'identified_date']

    def get_appetite(self, obj):
        a = obj.appetite_status
        return {'status': a['status'], 'score': a['score'], 'appetite': a['appetite'], 'tolerance': a['tolerance']}


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


class RiskAppetiteSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    risks_outside = serializers.SerializerMethodField()

    class Meta:
        model = RiskAppetite
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        appetite = attrs.get('max_acceptable_score', getattr(self.instance, 'max_acceptable_score', 12))
        tolerance = attrs.get('tolerance_score', getattr(self.instance, 'tolerance_score', 16))
        if not (1 <= appetite <= 25 and 1 <= tolerance <= 25):
            raise serializers.ValidationError('Scores must be between 1 and 25')
        if tolerance < appetite:
            raise serializers.ValidationError({'tolerance_score': 'Tolerance cannot be lower than appetite'})
        return attrs

    def get_risks_outside(self, obj):
        qs = Risk.objects.filter(organization=obj.organization).exclude(status__in=['closed', 'pending_approval'])
        qs = qs.filter(category=obj.category) if obj.category_id else qs
        return sum(1 for r in qs if r.appetite_status['status'] != 'within')


class KRIMeasurementSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)

    class Meta:
        model = KRIMeasurement
        fields = '__all__'
        read_only_fields = ['created_at', 'status', 'recorded_by']


class KeyRiskIndicatorSerializer(serializers.ModelSerializer):
    risk_title = serializers.CharField(source='risk.title', read_only=True)
    risk_code = serializers.CharField(source='risk.risk_id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    is_measurement_overdue = serializers.BooleanField(read_only=True)
    measurement_due_date = serializers.DateField(read_only=True)
    recent_measurements = serializers.SerializerMethodField()

    class Meta:
        model = KeyRiskIndicator
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'current_value', 'current_status', 'last_measured_at', 'created_by']

    def validate(self, attrs):
        direction = attrs.get('direction', getattr(self.instance, 'direction', 'up_bad'))
        warn = attrs.get('warning_threshold', getattr(self.instance, 'warning_threshold', None))
        crit = attrs.get('critical_threshold', getattr(self.instance, 'critical_threshold', None))
        if warn is not None and crit is not None:
            if direction == 'up_bad' and crit < warn:
                raise serializers.ValidationError({'critical_threshold': 'Must be >= warning threshold when higher is worse'})
            if direction == 'down_bad' and crit > warn:
                raise serializers.ValidationError({'critical_threshold': 'Must be <= warning threshold when lower is worse'})
        return attrs

    def get_recent_measurements(self, obj):
        return KRIMeasurementSerializer(obj.measurements.all()[:12], many=True).data


class KeyRiskIndicatorListSerializer(serializers.ModelSerializer):
    risk_code = serializers.CharField(source='risk.risk_id', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    is_measurement_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = KeyRiskIndicator
        fields = ['id', 'kri_id', 'name', 'name_ar', 'risk', 'risk_code', 'unit', 'direction', 'frequency',
                  'warning_threshold', 'critical_threshold', 'target_value', 'current_value', 'current_status',
                  'last_measured_at', 'is_measurement_overdue', 'owner_name', 'is_active']
