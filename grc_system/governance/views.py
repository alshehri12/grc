"""
Governance app views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import PolicyCategory, Policy, PolicyVersion, PolicyAcknowledgment, Procedure, Document
from .serializers import (
    PolicyCategorySerializer, PolicySerializer, PolicyListSerializer,
    PolicyVersionSerializer, PolicyAcknowledgmentSerializer,
    ProcedureSerializer, ProcedureListSerializer,
    DocumentSerializer, DocumentListSerializer
)


class PolicyCategoryViewSet(viewsets.ModelViewSet):
    queryset = PolicyCategory.objects.all()
    serializer_class = PolicyCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'name_ar', 'code']


class PolicyViewSet(viewsets.ModelViewSet):
    queryset = Policy.objects.select_related(
        'organization', 'category', 'owner', 'department', 'approved_by', 'created_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'category', 'status', 'classification', 'owner']
    search_fields = ['title', 'title_ar', 'policy_id']
    ordering_fields = ['updated_at', 'effective_date', 'review_date']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PolicyListSerializer
        return PolicySerializer
    
    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        policy = self.get_object()
        policy.status = 'pending_review'
        policy.save()
        return Response({'status': 'pending_review'})
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        from django.utils import timezone
        policy = self.get_object()
        policy.status = 'approved'
        policy.approved_by = request.user
        policy.approved_date = timezone.now().date()
        policy.save()
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        policy = self.get_object()
        if policy.status != 'approved':
            return Response({'error': 'Policy must be approved first'}, status=400)
        policy.status = 'published'
        policy.save()
        return Response({'status': 'published'})
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get policies pending review."""
        policies = self.queryset.filter(status='pending_review')
        serializer = PolicyListSerializer(policies, many=True)
        return Response(serializer.data)


class PolicyVersionViewSet(viewsets.ModelViewSet):
    queryset = PolicyVersion.objects.select_related('policy', 'created_by').all()
    serializer_class = PolicyVersionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['policy']
    ordering = ['-created_at']


class PolicyAcknowledgmentViewSet(viewsets.ModelViewSet):
    queryset = PolicyAcknowledgment.objects.select_related('policy', 'user').all()
    serializer_class = PolicyAcknowledgmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['policy', 'user']
    
    @action(detail=False, methods=['post'])
    def acknowledge(self, request):
        """Acknowledge a policy."""
        policy_id = request.data.get('policy_id')
        try:
            policy = Policy.objects.get(id=policy_id)
        except Policy.DoesNotExist:
            return Response({'error': 'Policy not found'}, status=404)
        
        ack, created = PolicyAcknowledgment.objects.get_or_create(
            policy=policy,
            user=request.user,
            version=policy.version,
            defaults={'ip_address': request.META.get('REMOTE_ADDR')}
        )
        
        if not created:
            return Response({'message': 'Already acknowledged'}, status=200)
        
        return Response(PolicyAcknowledgmentSerializer(ack).data, status=201)


class ProcedureViewSet(viewsets.ModelViewSet):
    queryset = Procedure.objects.select_related(
        'organization', 'policy', 'owner', 'department', 'created_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'policy', 'status', 'owner']
    search_fields = ['title', 'title_ar', 'procedure_id']
    ordering_fields = ['updated_at', 'effective_date']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProcedureListSerializer
        return ProcedureSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related(
        'organization', 'owner', 'department', 'created_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'document_type', 'status', 'classification']
    search_fields = ['title', 'title_ar', 'document_id']
    ordering_fields = ['updated_at', 'effective_date']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer
