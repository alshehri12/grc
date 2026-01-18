"""
BCM app serializers.
"""
from rest_framework import serializers
from .models import (
    BusinessFunction, BusinessImpactAnalysis, BCPlan, DisasterRecoveryPlan,
    CrisisManagementTeam, CrisisTeamMember, CallTree, CallTreeNode,
    CrisisIncident, BCMTest, BCMTestFinding
)


class BusinessFunctionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = BusinessFunction
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'department': {'required': False, 'allow_null': True},
            'owner': {'required': False, 'allow_null': True},
            'parent_function': {'required': False, 'allow_null': True},
            'created_by': {'required': False, 'allow_null': True},
        }


class BusinessFunctionListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = BusinessFunction
        fields = ['id', 'function_id', 'name', 'name_ar', 'criticality', 'status', 
                  'department_name', 'owner_name']


class BusinessImpactAnalysisSerializer(serializers.ModelSerializer):
    function_name = serializers.CharField(source='business_function.name', read_only=True)
    assessor_name = serializers.CharField(source='assessor.get_full_name', read_only=True)
    
    class Meta:
        model = BusinessImpactAnalysis
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'business_function': {'required': False, 'allow_null': True},
            'assessor': {'required': False, 'allow_null': True},
            'approved_by': {'required': False, 'allow_null': True},
        }


class BCPlanSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    covered_functions = serializers.PrimaryKeyRelatedField(
        queryset=BusinessFunction.objects.all(), 
        many=True, 
        required=False
    )
    
    class Meta:
        model = BCPlan
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'owner': {'required': False, 'allow_null': True},
            'approved_by': {'required': False, 'allow_null': True},
            'created_by': {'required': False, 'allow_null': True},
        }


class BCPlanListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = BCPlan
        fields = ['id', 'plan_id', 'title', 'title_ar', 'version', 'status', 
                  'owner_name', 'effective_date', 'review_date', 'last_tested_date']


class DisasterRecoveryPlanSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    bc_plan_title = serializers.CharField(source='bc_plan.title', read_only=True)
    
    class Meta:
        model = DisasterRecoveryPlan
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'bc_plan': {'required': False, 'allow_null': True},
            'owner': {'required': False, 'allow_null': True},
            'approved_by': {'required': False, 'allow_null': True},
            'created_by': {'required': False, 'allow_null': True},
        }


class CrisisTeamMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = CrisisTeamMember
        fields = '__all__'


class CrisisManagementTeamSerializer(serializers.ModelSerializer):
    members = CrisisTeamMemberSerializer(many=True, read_only=True)
    
    class Meta:
        model = CrisisManagementTeam
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CallTreeNodeSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = CallTreeNode
        fields = '__all__'


class CallTreeSerializer(serializers.ModelSerializer):
    nodes = CallTreeNodeSerializer(many=True, read_only=True)
    root_caller_name = serializers.CharField(source='root_caller.get_full_name', read_only=True)
    
    class Meta:
        model = CallTree
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CrisisIncidentSerializer(serializers.ModelSerializer):
    incident_commander_name = serializers.CharField(source='incident_commander.get_full_name', read_only=True)
    reported_by_name = serializers.CharField(source='reported_by.get_full_name', read_only=True)
    
    class Meta:
        model = CrisisIncident
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CrisisIncidentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisisIncident
        fields = ['id', 'incident_id', 'title', 'title_ar', 'incident_type', 
                  'severity', 'status', 'reported_at']


class BCMTestFindingSerializer(serializers.ModelSerializer):
    test_title = serializers.CharField(source='test.title', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = BCMTestFinding
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class BCMTestSerializer(serializers.ModelSerializer):
    coordinator_name = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    findings = BCMTestFindingSerializer(many=True, read_only=True)
    
    class Meta:
        model = BCMTest
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'bc_plan': {'required': False, 'allow_null': True},
            'dr_plan': {'required': False, 'allow_null': True},
            'coordinator': {'required': False, 'allow_null': True},
            'created_by': {'required': False, 'allow_null': True},
        }


class BCMTestListSerializer(serializers.ModelSerializer):
    coordinator_name = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    
    class Meta:
        model = BCMTest
        fields = ['id', 'test_id', 'title', 'title_ar', 'test_type', 'status',
                  'coordinator_name', 'scheduled_date', 'overall_result']
