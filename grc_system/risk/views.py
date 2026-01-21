"""
Risk app views.
"""
import json
import time
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count

from .models import AssetCategory, Asset, RiskCategory, Risk, RiskAssessment, RiskTreatment, RiskAcceptance
from .serializers import (
    AssetCategorySerializer, AssetSerializer, AssetListSerializer,
    RiskCategorySerializer, RiskSerializer, RiskListSerializer,
    RiskAssessmentSerializer, RiskTreatmentSerializer, RiskAcceptanceSerializer
)

# region agent log
DEBUG_LOG_PATH = r'c:\Users\aalshehre\GRC\grc_system\grc\.cursor\debug.log'
def debug_log(location, message, data, hypothesis_id):
    try:
        log_entry = json.dumps({'location': location, 'message': message, 'data': data, 'timestamp': int(time.time() * 1000), 'sessionId': 'debug-session', 'hypothesisId': hypothesis_id})
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except: pass
# endregion


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ar', 'code']


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related(
        'organization', 'category', 'owner', 'custodian', 'department'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'category', 'criticality', 'status', 'owner']
    search_fields = ['name', 'name_ar', 'asset_id']
    ordering_fields = ['name', 'criticality', 'created_at']
    ordering = ['-criticality', 'name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        return AssetSerializer


class RiskCategoryViewSet(viewsets.ModelViewSet):
    queryset = RiskCategory.objects.all()
    serializer_class = RiskCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'name_ar', 'code']


class RiskViewSet(viewsets.ModelViewSet):
    queryset = Risk.objects.select_related(
        'organization', 'category', 'owner', 'department', 'created_by'
    ).prefetch_related('assets', 'controls').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'category', 'risk_type', 'status', 'owner']
    search_fields = ['title', 'title_ar', 'risk_id', 'description']
    ordering_fields = ['inherent_likelihood', 'inherent_impact', 'identified_date', 'updated_at']
    ordering = ['-inherent_likelihood', '-inherent_impact']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RiskListSerializer
        return RiskSerializer
    
    # region agent log
    def create(self, request, *args, **kwargs):
        debug_log('RiskViewSet.create:entry', 'Create risk request received', {'request_data': request.data, 'user': str(request.user)}, 'RISK')
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            debug_log('RiskViewSet.create:validation_error', 'Serializer validation failed', {'errors': serializer.errors, 'data': request.data}, 'RISK')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        debug_log('RiskViewSet.create:validation_passed', 'Serializer validation passed', {}, 'RISK')
        try:
            self.perform_create(serializer)
            debug_log('RiskViewSet.create:success', 'Risk created successfully', {'risk_id': serializer.data.get('id')}, 'RISK')
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            debug_log('RiskViewSet.create:exception', 'Exception during risk creation', {'error': str(e), 'error_type': type(e).__name__}, 'RISK')
            raise
    # endregion
    
    @action(detail=False, methods=['get'])
    def matrix(self, request):
        """Get risk matrix data."""
        org_id = request.query_params.get('organization')
        risks = self.queryset
        if org_id:
            risks = risks.filter(organization_id=org_id)
        
        # Create 5x5 matrix
        matrix = [[[] for _ in range(5)] for _ in range(5)]
        
        for risk in risks.filter(status__in=['identified', 'assessed', 'treating', 'monitoring']):
            likelihood = min(risk.inherent_likelihood - 1, 4)
            impact = min(risk.inherent_impact - 1, 4)
            matrix[4 - likelihood][impact].append({
                'id': risk.id,
                'risk_id': risk.risk_id,
                'title': risk.title,
                'title_ar': risk.title_ar,
            })
        
        return Response({'matrix': matrix})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get risk statistics."""
        org_id = request.query_params.get('organization')
        risks = self.queryset
        if org_id:
            risks = risks.filter(organization_id=org_id)
        
        stats = {
            'total': risks.count(),
            'by_status': dict(risks.values_list('status').annotate(count=Count('id'))),
            'by_type': dict(risks.values_list('risk_type').annotate(count=Count('id'))),
            'by_level': {
                'critical': risks.filter(inherent_likelihood__gte=4, inherent_impact__gte=4).count(),
                'high': risks.filter(inherent_likelihood__gte=3, inherent_impact__gte=3).exclude(
                    inherent_likelihood__gte=4, inherent_impact__gte=4
                ).count(),
                'medium': risks.filter(inherent_likelihood__gte=2, inherent_impact__gte=2).exclude(
                    inherent_likelihood__gte=3, inherent_impact__gte=3
                ).count(),
                'low': risks.filter(inherent_likelihood__lte=2).filter(inherent_impact__lte=2).count(),
            }
        }
        return Response(stats)


class RiskAssessmentViewSet(viewsets.ModelViewSet):
    queryset = RiskAssessment.objects.select_related('risk', 'assessor', 'approved_by').all()
    serializer_class = RiskAssessmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['risk', 'assessment_type', 'status', 'assessor']
    ordering = ['-assessment_date']


class RiskTreatmentViewSet(viewsets.ModelViewSet):
    queryset = RiskTreatment.objects.select_related('risk', 'owner', 'created_by').all()
    serializer_class = RiskTreatmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['risk', 'treatment_option', 'status', 'owner']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        treatment = self.get_object()
        treatment.progress_percentage = request.data.get('progress', treatment.progress_percentage)
        treatment.progress_notes = request.data.get('notes', treatment.progress_notes)
        treatment.save()
        return Response(RiskTreatmentSerializer(treatment).data)


class RiskAcceptanceViewSet(viewsets.ModelViewSet):
    queryset = RiskAcceptance.objects.select_related('risk', 'requested_by', 'approved_by').all()
    serializer_class = RiskAcceptanceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['risk', 'status', 'requested_by']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        from django.utils import timezone
        acceptance = self.get_object()
        acceptance.status = 'approved'
        acceptance.approved_by = request.user
        acceptance.approved_date = timezone.now().date()
        acceptance.approval_comments = request.data.get('comments', '')
        acceptance.save()
        return Response(RiskAcceptanceSerializer(acceptance).data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        from django.utils import timezone
        acceptance = self.get_object()
        acceptance.status = 'rejected'
        acceptance.approved_by = request.user
        acceptance.approved_date = timezone.now().date()
        acceptance.approval_comments = request.data.get('comments', '')
        acceptance.save()
        return Response(RiskAcceptanceSerializer(acceptance).data)
