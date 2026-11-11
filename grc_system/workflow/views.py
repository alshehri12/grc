"""
Workflow app views.

  * Templates/steps: readable by all, editable by admins.
  * Instances/approvals: read-only records; state changes go through
    WorkflowService actions (approve/reject/delegate/cancel) which enforce
    segregation of duties and write the audit trail.
  * Non-admins only see workflows and approvals they are party to.
"""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from core.audit import AuditedModelViewSet, log_action
from core.permissions import IsAdminOrReadOnly, user_is_admin, user_is_manager, get_user_department
from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, Approval, Task
from .serializers import (
    WorkflowTemplateSerializer, WorkflowStepSerializer,
    WorkflowInstanceSerializer, ApprovalSerializer, TaskSerializer
)
from .services import WorkflowService, WorkflowPermissionError


def _error(exc):
    code = status.HTTP_403_FORBIDDEN if isinstance(exc, WorkflowPermissionError) else status.HTTP_400_BAD_REQUEST
    return Response({'error': str(exc)}, status=code)


class WorkflowTemplateViewSet(AuditedModelViewSet):
    queryset = WorkflowTemplate.objects.prefetch_related('steps').all()
    serializer_class = WorkflowTemplateSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['workflow_type', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class WorkflowStepViewSet(AuditedModelViewSet):
    queryset = WorkflowStep.objects.select_related('template').all()
    serializer_class = WorkflowStepSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template', 'step_type']


class WorkflowInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkflowInstance.objects.select_related('template', 'initiated_by').all()
    serializer_class = WorkflowInstanceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['template', 'status', 'initiated_by', 'content_type']
    search_fields = ['object_title']
    ordering_fields = ['started_at', 'due_date']
    ordering = ['-started_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user_is_admin(user):
            return qs
        visible = Q(initiated_by=user) | Q(approvals__assignee=user)
        if user_is_manager(user):
            dept = get_user_department(user)
            if dept:
                visible |= Q(initiated_by__profile__department=dept)
        return qs.filter(visible).distinct()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        try:
            WorkflowService.cancel_workflow(instance, request.user, request.data.get('reason', ''), request=request)
        except (ValueError, WorkflowPermissionError) as exc:
            return _error(exc)
        return Response(WorkflowInstanceSerializer(instance).data)


class ApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Approval.objects.select_related(
        'workflow_instance', 'workflow_instance__template', 'workflow_instance__initiated_by',
        'step', 'assignee', 'decided_by'
    ).all()
    serializer_class = ApprovalSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['workflow_instance', 'assignee', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user_is_admin(user):
            return qs
        return qs.filter(Q(assignee=user) | Q(decided_by=user) | Q(workflow_instance__initiated_by=user)).distinct()

    @action(detail=False, methods=['get'])
    def my_pending(self, request):
        approvals = self.get_queryset().filter(assignee=request.user, status='pending').order_by('due_date')
        return Response(self.get_serializer(approvals, many=True).data)

    def _decide(self, request, decision):
        approval = self.get_object()
        try:
            approval, finished = WorkflowService.handle_approval_decision(
                approval, decision, request.user, request.data.get('comments', ''), request=request)
        except (ValueError, WorkflowPermissionError) as exc:
            return _error(exc)
        return Response({**ApprovalSerializer(approval).data, 'workflow_completed': finished})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, 'approved')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, 'rejected')

    @action(detail=True, methods=['post'])
    def delegate(self, request, pk=None):
        approval = self.get_object()
        to_user_id = request.data.get('to_user_id')
        if not to_user_id:
            return Response({'error': 'to_user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            to_user = get_user_model().objects.get(pk=to_user_id, is_active=True)
        except get_user_model().DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            WorkflowService.delegate_approval(approval, request.user, to_user, request.data.get('reason', ''), request=request)
        except (ValueError, WorkflowPermissionError) as exc:
            return _error(exc)
        return Response(ApprovalSerializer(approval).data)


class TaskViewSet(AuditedModelViewSet):
    queryset = Task.objects.select_related('assigned_to', 'assigned_by').all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['assigned_to', 'status', 'priority', 'task_type']
    search_fields = ['title', 'title_ar', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']
    ordering = ['-priority', 'due_date']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user_is_admin(user) or user_is_manager(user):
            return qs
        return qs.filter(Q(assigned_to=user) | Q(assigned_by=user))

    def perform_create(self, serializer):
        serializer.validated_data.setdefault('assigned_by', self.request.user)
        return super().perform_create(serializer)

    def _can_work(self, task, user):
        return user_is_admin(user) or user.pk in (task.assigned_to_id, task.assigned_by_id)

    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        tasks = self.queryset.filter(assigned_to=request.user).exclude(status__in=['completed', 'cancelled'])
        return Response(self.get_serializer(tasks, many=True).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        if not self._can_work(task, request.user):
            return Response({'error': 'Only the assignee can start this task'}, status=status.HTTP_403_FORBIDDEN)
        task.status = 'in_progress'
        task.started_at = timezone.now()
        task.save(update_fields=['status', 'started_at', 'updated_at'])
        log_action(request.user, 'update', task, changes={'status': ['pending', 'in_progress']}, request=request)
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        if not self._can_work(task, request.user):
            return Response({'error': 'Only the assignee can complete this task'}, status=status.HTTP_403_FORBIDDEN)
        previous = task.status
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.completion_notes = request.data.get('notes', '')
        task.save(update_fields=['status', 'completed_at', 'completion_notes', 'updated_at'])
        log_action(request.user, 'update', task, changes={'status': [previous, 'completed']}, request=request)
        from .signals import task_completed
        task_completed.send(sender=self.__class__, task=task, completed_by=request.user)
        return Response(TaskSerializer(task).data)
