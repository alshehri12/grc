"""
Compliance app views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count, Avg

from .models import (
    ControlFramework, ControlDomain, Control, ControlImplementation,
    Audit, AuditFinding, CorrectiveAction, Evidence, GapAssessment
)
from .serializers import (
    ControlFrameworkSerializer, ControlDomainSerializer,
    ControlSerializer, ControlListSerializer, ControlImplementationSerializer,
    AuditSerializer, AuditListSerializer,
    AuditFindingSerializer, AuditFindingListSerializer,
    CorrectiveActionSerializer, EvidenceSerializer, EvidenceListSerializer,
    GapAssessmentSerializer, GapAssessmentListSerializer
)


class ControlFrameworkViewSet(viewsets.ModelViewSet):
    queryset = ControlFramework.objects.prefetch_related('domains').all()
    serializer_class = ControlFrameworkSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_mandatory', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class ControlDomainViewSet(viewsets.ModelViewSet):
    queryset = ControlDomain.objects.select_related('framework', 'parent').all()
    serializer_class = ControlDomainSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['framework', 'parent']
    search_fields = ['name', 'name_ar', 'code']


class ControlViewSet(viewsets.ModelViewSet):
    queryset = Control.objects.select_related('domain', 'domain__framework').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['domain', 'domain__framework', 'control_type']
    search_fields = ['title', 'title_ar', 'control_id', 'description']
    ordering = ['domain', 'order', 'control_id']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ControlListSerializer
        return ControlSerializer
    
    def create(self, request, *args, **kwargs):
        # #region agent log
        import json
        from django.utils import timezone
        log_entry = {
            "location": "ControlViewSet.create:entry",
            "message": "Create control request received",
            "data": {"request_data": request.data},
            "timestamp": timezone.now().timestamp() * 1000,
            "sessionId": "debug-session",
            "hypothesisId": "CONTROL"
        }
        with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        # #endregion
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # #region agent log
            log_entry = {
                "location": "ControlViewSet.create:validation_error",
                "message": "Serializer validation failed",
                "data": {"errors": serializer.errors, "data": serializer.initial_data},
                "timestamp": timezone.now().timestamp() * 1000,
                "sessionId": "debug-session",
                "hypothesisId": "CONTROL"
            }
            with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            # #endregion
            return Response(serializer.errors, status=400)
        control = serializer.save()
        # #region agent log
        log_entry = {
            "location": "ControlViewSet.create:success",
            "message": "Control created successfully",
            "data": {"id": control.id},
            "timestamp": timezone.now().timestamp() * 1000,
            "sessionId": "debug-session",
            "hypothesisId": "CONTROL"
        }
        with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        # #endregion
        return Response(self.get_serializer(control).data, status=201)
    
    @action(detail=False, methods=['get'])
    def by_framework(self, request):
        """Get controls grouped by framework and domain."""
        framework_id = request.query_params.get('framework')
        if not framework_id:
            return Response({'error': 'framework parameter required'}, status=400)
        
        domains = ControlDomain.objects.filter(
            framework_id=framework_id
        ).prefetch_related('controls').order_by('order', 'code')
        
        result = []
        for domain in domains:
            result.append({
                'id': domain.id,
                'code': domain.code,
                'name': domain.name,
                'name_ar': domain.name_ar,
                'controls': ControlListSerializer(domain.controls.all(), many=True).data
            })
        
        return Response(result)


class ControlImplementationViewSet(viewsets.ModelViewSet):
    queryset = ControlImplementation.objects.select_related(
        'organization', 'control', 'control__domain', 'owner', 'department'
    ).all()
    serializer_class = ControlImplementationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization', 'control', 'control__domain__framework', 'status', 'owner']
    ordering = ['control__control_id']
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get implementation statistics."""
        org_id = request.query_params.get('organization')
        framework_id = request.query_params.get('framework')
        
        impls = self.queryset
        if org_id:
            impls = impls.filter(organization_id=org_id)
        if framework_id:
            impls = impls.filter(control__domain__framework_id=framework_id)
        
        stats = {
            'total': impls.count(),
            'by_status': dict(impls.values_list('status').annotate(count=Count('id'))),
            'avg_maturity': impls.aggregate(avg=Avg('maturity_level'))['avg'],
            'by_maturity': dict(impls.values_list('maturity_level').annotate(count=Count('id'))),
        }
        return Response(stats)


class AuditViewSet(viewsets.ModelViewSet):
    queryset = Audit.objects.select_related(
        'organization', 'lead_auditor', 'created_by'
    ).prefetch_related('frameworks', 'departments', 'auditors').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'audit_type', 'status', 'lead_auditor']
    search_fields = ['title', 'title_ar', 'audit_id']
    ordering = ['-planned_start_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditListSerializer
        return AuditSerializer
    
    def create(self, request, *args, **kwargs):
        # #region agent log
        import json
        from django.utils import timezone
        log_entry = {
            "location": "AuditViewSet.create:entry",
            "message": "Create audit request received",
            "data": {"request_data": request.data},
            "timestamp": timezone.now().timestamp() * 1000,
            "sessionId": "debug-session",
            "hypothesisId": "AUDIT"
        }
        with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        # #endregion
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # #region agent log
            log_entry = {
                "location": "AuditViewSet.create:validation_error",
                "message": "Serializer validation failed",
                "data": {"errors": serializer.errors, "data": serializer.initial_data},
                "timestamp": timezone.now().timestamp() * 1000,
                "sessionId": "debug-session",
                "hypothesisId": "AUDIT"
            }
            with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            # #endregion
            return Response(serializer.errors, status=400)
        audit = serializer.save()
        # #region agent log
        log_entry = {
            "location": "AuditViewSet.create:success",
            "message": "Audit created successfully",
            "data": {"id": audit.id},
            "timestamp": timezone.now().timestamp() * 1000,
            "sessionId": "debug-session",
            "hypothesisId": "AUDIT"
        }
        with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        # #endregion
        return Response(self.get_serializer(audit).data, status=201)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        from django.utils import timezone
        audit = self.get_object()
        audit.status = 'in_progress'
        audit.actual_start_date = timezone.now().date()
        audit.save()
        return Response(AuditSerializer(audit).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        from django.utils import timezone
        audit = self.get_object()
        audit.status = 'completed'
        audit.actual_end_date = timezone.now().date()
        audit.save()
        return Response(AuditSerializer(audit).data)


class AuditFindingViewSet(viewsets.ModelViewSet):
    queryset = AuditFinding.objects.select_related(
        'audit', 'control', 'assigned_to', 'department', 'closed_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['audit', 'finding_type', 'status', 'assigned_to']
    search_fields = ['title', 'title_ar', 'finding_id']
    ordering = ['-finding_type', '-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditFindingListSerializer
        return AuditFindingSerializer
    
    @action(detail=False, methods=['get'])
    def open_findings(self, request):
        """Get all open findings."""
        org_id = request.query_params.get('organization')
        findings = self.queryset.filter(status__in=['open', 'in_progress'])
        if org_id:
            findings = findings.filter(audit__organization_id=org_id)
        serializer = AuditFindingListSerializer(findings, many=True)
        return Response(serializer.data)


class CorrectiveActionViewSet(viewsets.ModelViewSet):
    queryset = CorrectiveAction.objects.select_related(
        'organization', 'finding', 'owner', 'verified_by', 'created_by'
    ).all()
    serializer_class = CorrectiveActionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization', 'finding', 'status', 'priority', 'owner']
    ordering = ['-priority', 'target_date']
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        from django.utils import timezone
        car = self.get_object()
        car.status = 'verified'
        car.verified_by = request.user
        car.verified_date = timezone.now().date()
        car.verification_notes = request.data.get('notes', '')
        car.save()
        return Response(CorrectiveActionSerializer(car).data)


class EvidenceViewSet(viewsets.ModelViewSet):
    queryset = Evidence.objects.select_related(
        'organization', 'control_implementation', 'control_implementation__control',
        'submitted_by', 'reviewed_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'control_implementation', 'evidence_type', 'status']
    search_fields = ['title', 'title_ar', 'evidence_id']
    ordering = ['-collection_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EvidenceListSerializer
        return EvidenceSerializer
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get evidence expiring within 30 days."""
        from django.utils import timezone
        from datetime import timedelta
        
        org_id = request.query_params.get('organization')
        threshold = timezone.now().date() + timedelta(days=30)
        
        evidence = self.queryset.filter(
            valid_until__lte=threshold,
            status__in=['submitted', 'accepted']
        )
        if org_id:
            evidence = evidence.filter(organization_id=org_id)
        
        serializer = EvidenceListSerializer(evidence, many=True)
        return Response(serializer.data)


class GapAssessmentViewSet(viewsets.ModelViewSet):
    queryset = GapAssessment.objects.select_related(
        'organization', 'framework', 'assessor', 'approved_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'framework', 'status']
    search_fields = ['title', 'title_ar', 'assessment_id']
    ordering = ['-assessment_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return GapAssessmentListSerializer
        return GapAssessmentSerializer
    
    @action(detail=True, methods=['post'])
    def calculate_score(self, request, pk=None):
        """Recalculate compliance score."""
        assessment = self.get_object()
        assessment.compliance_score = assessment.calculate_compliance_score()
        assessment.save()
        return Response(GapAssessmentSerializer(assessment).data)
