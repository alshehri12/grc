"""
Notifications app views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import NotificationTemplate, Notification, Reminder, Escalation
from .serializers import (
    NotificationTemplateSerializer, NotificationSerializer,
    ReminderSerializer, EscalationSerializer
)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['event_type', 'channel', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.select_related('recipient', 'template').all()
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['recipient', 'status', 'channel', 'priority']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def my_notifications(self, request):
        """Get current user's notifications."""
        notifications = self.queryset.filter(recipient=request.user)
        unread = request.query_params.get('unread')
        if unread == 'true':
            notifications = notifications.filter(read_at__isnull=True)
        serializer = self.get_serializer(notifications[:50], many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count."""
        count = self.queryset.filter(recipient=request.user, read_at__isnull=True).count()
        return Response({'count': count})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.status = 'read'
        notification.save()
        return Response(NotificationSerializer(notification).data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        self.queryset.filter(recipient=request.user, read_at__isnull=True).update(
            read_at=timezone.now(),
            status='read'
        )
        return Response({'status': 'success'})


class ReminderViewSet(viewsets.ModelViewSet):
    queryset = Reminder.objects.select_related('recipient', 'created_by').all()
    serializer_class = ReminderSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['recipient', 'status', 'frequency']
    ordering = ['scheduled_date']


class EscalationViewSet(viewsets.ModelViewSet):
    queryset = Escalation.objects.select_related(
        'escalated_from', 'escalated_to', 'resolved_by'
    ).all()
    serializer_class = EscalationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'level', 'escalated_to']
    ordering = ['-escalated_at']
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        escalation = self.get_object()
        escalation.status = 'resolved'
        escalation.resolved_by = request.user
        escalation.resolved_at = timezone.now()
        escalation.resolution_notes = request.data.get('notes', '')
        escalation.save()
        return Response(EscalationSerializer(escalation).data)
