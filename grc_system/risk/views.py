"""
Risk app views.
"""
from rest_framework import viewsets, status
from core.audit import AuditedModelViewSet
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



class AssetCategoryViewSet(AuditedModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ar', 'code']


class AssetViewSet(AuditedModelViewSet):
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


class RiskCategoryViewSet(AuditedModelViewSet):
    queryset = RiskCategory.objects.all()
    serializer_class = RiskCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'name_ar', 'code']


class RiskViewSet(AuditedModelViewSet):
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
    
    
    @action(detail=False, methods=['get'])
    def matrix(self, request):
        """Get risk matrix data."""
        org_id = request.query_params.get('organization')
        risks = self.queryset
        if org_id:
            risks = risks.filter(organization_id=org_id)
        
        from risk.utils import get_risk_thresholds, get_risk_levels, build_matrix_cells

        # Create 5x5 matrix (rows = likelihood 5..1, columns = impact 1..5)
        matrix = [[[] for _ in range(5)] for _ in range(5)]

        for risk in risks.filter(status__in=['identified', 'assessed', 'treating', 'monitoring']):
            likelihood = min(risk.inherent_likelihood - 1, 4)
            impact = min(risk.inherent_impact - 1, 4)
            matrix[4 - likelihood][impact].append({
                'id': risk.id,
                'risk_id': risk.risk_id,
                'title': risk.title,
                'title_ar': risk.title_ar,
                'score': risk.inherent_risk_score,
                'level': risk.risk_level,
            })

        return Response({
            'matrix': matrix,
            'thresholds': get_risk_thresholds(org_id),
            'levels': get_risk_levels(org_id),
            'cells': build_matrix_cells(org_id),
        })

    @action(detail=False, methods=['get'])
    def matrix_config(self, request):
        """Risk level thresholds and labels used everywhere (model, stats, dashboard, UI)."""
        from risk.utils import get_risk_thresholds, get_risk_levels, LIKELIHOOD_LABELS, IMPACT_LABELS
        org_id = request.query_params.get('organization')
        return Response({
            'thresholds': get_risk_thresholds(org_id),
            'levels': get_risk_levels(org_id),
            'likelihood_labels': LIKELIHOOD_LABELS,
            'impact_labels': IMPACT_LABELS,
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get risk statistics."""
        org_id = request.query_params.get('organization')
        risks = self.queryset
        if org_id:
            risks = risks.filter(organization_id=org_id)
        
        from risk.utils import get_risk_level, get_risk_thresholds

        by_level = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        residual_by_level = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for likelihood, impact, r_likelihood, r_impact in risks.values_list(
                'inherent_likelihood', 'inherent_impact', 'residual_likelihood', 'residual_impact'):
            by_level[get_risk_level(likelihood * impact, org_id)] += 1
            if r_likelihood and r_impact:
                residual_by_level[get_risk_level(r_likelihood * r_impact, org_id)] += 1

        stats = {
            'total': risks.count(),
            'by_status': dict(risks.values_list('status').annotate(count=Count('id'))),
            'by_type': dict(risks.values_list('risk_type').annotate(count=Count('id'))),
            'by_level': by_level,
            'residual_by_level': residual_by_level,
            'thresholds': get_risk_thresholds(org_id),
        }
        return Response(stats)
    
    RESIDUAL_FIELDS = ('residual_likelihood', 'residual_impact')

    def perform_update(self, serializer):
        # A manual residual assessment switches off automatic (control-derived) residual.
        if any(f in self.request.data for f in self.RESIDUAL_FIELDS):
            serializer.validated_data['residual_auto'] = False
        return super().perform_update(serializer)

    @action(detail=True, methods=['post'])
    def calculate_residual(self, request, pk=None):
        """
        (Re)derive residual risk from linked control effectiveness and switch the
        risk back to automatic residual mode.
        POST /api/risk/risks/{id}/calculate_residual/
        """
        from core.audit import log_action
        risk = self.get_object()
        before = (risk.residual_likelihood, risk.residual_impact, risk.residual_auto)
        effect = risk.calculate_residual_from_controls()
        risk.residual_auto = True
        risk.save(update_fields=['residual_likelihood', 'residual_impact', 'residual_auto', 'updated_at'])
        log_action(request.user, 'update', risk, request=request, changes={
            'residual': [list(before[:2]), [risk.residual_likelihood, risk.residual_impact]],
            'residual_auto': [before[2], True]})
        return Response({
            'inherent_score': risk.inherent_risk_score,
            'residual_likelihood': risk.residual_likelihood,
            'residual_impact': risk.residual_impact,
            'residual_score': risk.residual_risk_score,
            'residual_level': risk.residual_risk_level,
            'risk_reduction': risk.risk_reduction_percentage,
            'control_effect': effect,
            'treatment_recommendation': risk.get_treatment_recommendation()
        })
    
    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        """
        Get comprehensive risk analysis.
        GET /api/risk/risks/{id}/analysis/
        """
        from risk.utils import get_risk_level, get_risk_color, check_risk_appetite
        
        risk = self.get_object()
        
        # Get appetite threshold from settings (default 12 = medium-high boundary)
        appetite_threshold = 12
        appetite_result = check_risk_appetite(risk, appetite_threshold)
        
        return Response({
            'risk_id': risk.risk_id,
            'title': risk.title,
            'inherent': {
                'likelihood': risk.inherent_likelihood,
                'impact': risk.inherent_impact,
                'score': risk.inherent_risk_score,
                'level': risk.risk_level,
                'color': get_risk_color(risk.inherent_risk_score)
            },
            'residual': {
                'likelihood': risk.residual_likelihood,
                'impact': risk.residual_impact,
                'score': risk.residual_risk_score,
                'level': risk.residual_risk_level,
                'color': get_risk_color(risk.residual_risk_score) if risk.residual_risk_score else None
            },
            'target': {
                'likelihood': risk.target_likelihood,
                'impact': risk.target_impact,
                'score': risk.target_risk_score
            },
            'risk_reduction': risk.risk_reduction_percentage,
            'linked_controls_count': risk.controls.count(),
            'treatment_recommendation': risk.get_treatment_recommendation(),
            'appetite_check': appetite_result,
            'active_treatments': risk.treatments.filter(status__in=['planned', 'in_progress']).count(),
        })
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get risks aggregated by category.
        GET /api/risk/risks/by_category/
        """
        from risk.utils import aggregate_risks_by_category
        
        org_id = request.query_params.get('organization')
        risks = self.queryset
        if org_id:
            risks = risks.filter(organization_id=org_id)
        
        return Response(aggregate_risks_by_category(risks))


class RiskAssessmentViewSet(AuditedModelViewSet):
    queryset = RiskAssessment.objects.select_related('risk', 'assessor', 'approved_by').all()
    serializer_class = RiskAssessmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['risk', 'assessment_type', 'status', 'assessor']
    ordering = ['-assessment_date']


class RiskTreatmentViewSet(AuditedModelViewSet):
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


class RiskAcceptanceViewSet(AuditedModelViewSet):
    queryset = RiskAcceptance.objects.select_related('risk', 'requested_by', 'approved_by').all()
    serializer_class = RiskAcceptanceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['risk', 'status', 'requested_by']
    ordering = ['-created_at']
    
    def _decide(self, request, decision):
        """
        Approve/reject a risk acceptance. Goes through the workflow approval when
        one is pending (so segregation of duties and audit trail apply); otherwise
        only a manager/admin who is not the requester may decide directly.
        """
        from django.utils import timezone
        from core.audit import log_action
        from core.permissions import user_can_approve
        from workflow.services import WorkflowService, WorkflowPermissionError

        acceptance = self.get_object()
        if acceptance.status != 'pending':
            return Response({'error': 'Acceptance has already been decided'}, status=status.HTTP_400_BAD_REQUEST)
        if acceptance.requested_by_id == request.user.pk:
            return Response({'error': 'You cannot decide your own acceptance request'}, status=status.HTTP_403_FORBIDDEN)
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)

        comments = request.data.get('comments', '')
        workflow = WorkflowService.get_workflow_for_object(acceptance)
        pending = workflow.approvals.filter(status='pending').first() if workflow else None
        try:
            if pending:
                WorkflowService.handle_approval_decision(pending, decision, request.user, comments, request=request)
                acceptance.refresh_from_db()
            else:
                acceptance.status = decision
            acceptance.approved_by = request.user
            acceptance.approved_date = timezone.now().date()
            acceptance.approval_comments = comments
            acceptance.save()
            if not pending:
                log_action(request.user, 'approve' if decision == 'approved' else 'reject', acceptance,
                           changes={'comments': comments}, request=request)
        except (ValueError, WorkflowPermissionError) as exc:
            code = status.HTTP_403_FORBIDDEN if isinstance(exc, WorkflowPermissionError) else status.HTTP_400_BAD_REQUEST
            return Response({'error': str(exc)}, status=code)
        return Response(RiskAcceptanceSerializer(acceptance).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, 'approved')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, 'rejected')
