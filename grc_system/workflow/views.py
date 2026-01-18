"""
Workflow app views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, Approval, Task
from .serializers import (
    WorkflowTemplateSerializer, WorkflowStepSerializer,
    WorkflowInstanceSerializer, ApprovalSerializer, TaskSerializer
)


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    queryset = WorkflowTemplate.objects.prefetch_related('steps').all()
    serializer_class = WorkflowTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['workflow_type', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class WorkflowStepViewSet(viewsets.ModelViewSet):
    queryset = WorkflowStep.objects.select_related('template').all()
    serializer_class = WorkflowStepSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template', 'step_type']


class WorkflowInstanceViewSet(viewsets.ModelViewSet):
    queryset = WorkflowInstance.objects.select_related('template', 'initiated_by').all()
    serializer_class = WorkflowInstanceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['template', 'status', 'initiated_by']
    search_fields = ['object_title']
    ordering_fields = ['started_at', 'due_date']
    ordering = ['-started_at']
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        instance.status = 'cancelled'
        instance.save()
        return Response({'status': 'cancelled'})


class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = Approval.objects.select_related(
        'workflow_instance', 'step', 'assignee', 'decided_by'
    ).all()
    serializer_class = ApprovalSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['workflow_instance', 'assignee', 'status']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def my_pending(self, request):
        """Get current user's pending approvals."""
        approvals = self.queryset.filter(assignee=request.user, status='pending')
        serializer = self.get_serializer(approvals, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        approval = self.get_object()
        approval.status = 'approved'
        approval.decided_by = request.user
        approval.decided_at = timezone.now()
        approval.comments = request.data.get('comments', '')
        approval.save()
        return Response(ApprovalSerializer(approval).data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        approval = self.get_object()
        approval.status = 'rejected'
        approval.decided_by = request.user
        approval.decided_at = timezone.now()
        approval.comments = request.data.get('comments', '')
        approval.save()
        return Response(ApprovalSerializer(approval).data)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('assigned_to', 'assigned_by').all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['assigned_to', 'status', 'priority', 'task_type']
    search_fields = ['title', 'title_ar', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']
    ordering = ['-priority', 'due_date']
    
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get current user's tasks."""
        tasks = self.queryset.filter(assigned_to=request.user).exclude(status='completed')
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        task.status = 'in_progress'
        task.started_at = timezone.now()
        task.save()
        return Response(TaskSerializer(task).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.completion_notes = request.data.get('notes', '')
        task.save()
        return Response(TaskSerializer(task).data)
