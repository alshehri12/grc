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
        """Approve a pending approval and advance the workflow."""
        from .services import WorkflowService
        
        approval = self.get_object()
        comments = request.data.get('comments', '')
        
        try:
            approval, workflow_completed = WorkflowService.handle_approval_decision(
                approval, 'approved', request.user, comments
            )
            return Response({
                **ApprovalSerializer(approval).data,
                'workflow_completed': workflow_completed
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an approval and update the workflow accordingly."""
        from .services import WorkflowService
        
        approval = self.get_object()
        comments = request.data.get('comments', '')
        
        try:
            approval, workflow_completed = WorkflowService.handle_approval_decision(
                approval, 'rejected', request.user, comments
            )
            return Response({
                **ApprovalSerializer(approval).data,
                'workflow_completed': workflow_completed
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def delegate(self, request, pk=None):
        """Delegate an approval to another user."""
        from .services import WorkflowService
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        approval = self.get_object()
        to_user_id = request.data.get('to_user_id')
        reason = request.data.get('reason', '')
        
        if not to_user_id:
            return Response({'error': 'to_user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            to_user = User.objects.get(pk=to_user_id)
            WorkflowService.delegate_approval(approval, request.user, to_user, reason)
            return Response(ApprovalSerializer(approval).data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
