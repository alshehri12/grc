"""
Workflow app serializers.
"""
from rest_framework import serializers
from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, Approval, Task


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = '__all__'


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkflowTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    initiated_by_name = serializers.CharField(source='initiated_by.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = WorkflowInstance
        fields = '__all__'
        read_only_fields = ['started_at', 'completed_at']


class ApprovalSerializer(serializers.ModelSerializer):
    workflow_title = serializers.CharField(source='workflow_instance.object_title', read_only=True)
    step_name = serializers.CharField(source='step.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.get_full_name', read_only=True)
    
    class Meta:
        model = Approval
        fields = '__all__'
        read_only_fields = ['created_at']


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
