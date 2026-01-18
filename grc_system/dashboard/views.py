"""
Dashboard app views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count, Avg, Q
from django.utils import timezone

from .models import (
    DashboardWidget, Dashboard, DashboardWidgetPosition,
    ReportTemplate, GeneratedReport, KPI, KPIValue
)
from .serializers import (
    DashboardWidgetSerializer, DashboardSerializer, DashboardListSerializer,
    ReportTemplateSerializer, GeneratedReportSerializer, GeneratedReportListSerializer,
    KPISerializer, KPIValueSerializer
)


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['widget_type', 'data_source', 'is_active']
    search_fields = ['name', 'name_ar']


class DashboardViewSet(viewsets.ModelViewSet):
    queryset = Dashboard.objects.prefetch_related(
        'widget_positions', 'widget_positions__widget', 'allowed_roles'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['dashboard_type', 'is_default', 'is_public', 'owner']
    search_fields = ['name', 'name_ar']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DashboardListSerializer
        return DashboardSerializer
    
    @action(detail=False, methods=['get'])
    def my_dashboards(self, request):
        """Get dashboards accessible to current user."""
        user = request.user
        dashboards = self.queryset.filter(
            Q(is_public=True) | 
            Q(owner=user) |
            Q(allowed_roles__in=user.profile.roles.all())
        ).distinct()
        serializer = DashboardListSerializer(dashboards, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def executive_summary(self, request):
        """Get executive summary data."""
        from risk.models import Risk
        from compliance.models import Audit, AuditFinding, ControlImplementation
        from workflow.models import Task
        from governance.models import Policy
        
        org_id = request.query_params.get('organization')
        
        # Risk summary
        risks = Risk.objects.all()
        if org_id:
            risks = risks.filter(organization_id=org_id)
        
        risk_summary = {
            'total': risks.count(),
            'critical': risks.filter(inherent_likelihood__gte=4, inherent_impact__gte=4).count(),
            'high': risks.filter(inherent_likelihood__gte=3, inherent_impact__gte=3).count(),
            'treating': risks.filter(status='treating').count(),
        }
        
        # Compliance summary
        impls = ControlImplementation.objects.all()
        if org_id:
            impls = impls.filter(organization_id=org_id)
        
        total_impls = impls.count()
        implemented = impls.filter(status='implemented').count()
        compliance_rate = (implemented / total_impls * 100) if total_impls > 0 else 0
        
        compliance_summary = {
            'total_controls': total_impls,
            'implemented': implemented,
            'compliance_rate': round(compliance_rate, 1),
            'avg_maturity': impls.aggregate(avg=Avg('maturity_level'))['avg'] or 0,
        }
        
        # Audit findings
        findings = AuditFinding.objects.all()
        if org_id:
            findings = findings.filter(audit__organization_id=org_id)
        
        findings_summary = {
            'total_open': findings.filter(status__in=['open', 'in_progress']).count(),
            'overdue': findings.filter(status__in=['open', 'in_progress'], due_date__lt=timezone.now().date()).count(),
            'major_nc': findings.filter(finding_type='major_nc', status__in=['open', 'in_progress']).count(),
        }
        
        # Tasks
        tasks = Task.objects.filter(assigned_to=request.user)
        tasks_summary = {
            'pending': tasks.filter(status='pending').count(),
            'in_progress': tasks.filter(status='in_progress').count(),
            'overdue': tasks.filter(status__in=['pending', 'in_progress'], due_date__lt=timezone.now()).count(),
        }
        
        # Policies
        policies = Policy.objects.all()
        if org_id:
            policies = policies.filter(organization_id=org_id)
        
        policies_summary = {
            'total': policies.count(),
            'published': policies.filter(status='published').count(),
            'pending_review': policies.filter(status='pending_review').count(),
            'expiring_soon': policies.filter(
                review_date__lte=timezone.now().date() + timezone.timedelta(days=30)
            ).count(),
        }
        
        return Response({
            'risks': risk_summary,
            'compliance': compliance_summary,
            'findings': findings_summary,
            'tasks': tasks_summary,
            'policies': policies_summary,
        })


class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['report_type', 'output_format', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class GeneratedReportViewSet(viewsets.ModelViewSet):
    queryset = GeneratedReport.objects.select_related('organization', 'template', 'generated_by').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization', 'template', 'status', 'generated_by']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return GeneratedReportListSerializer
        return GeneratedReportSerializer
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Queue a report for generation."""
        template_id = request.data.get('template_id')
        org_id = request.data.get('organization_id')
        parameters = request.data.get('parameters', {})
        
        try:
            template = ReportTemplate.objects.get(id=template_id)
        except ReportTemplate.DoesNotExist:
            return Response({'error': 'Template not found'}, status=404)
        
        report = GeneratedReport.objects.create(
            organization_id=org_id,
            template=template,
            title=f"{template.name} - {timezone.now().strftime('%Y-%m-%d')}",
            status='pending',
            parameters=parameters,
            generated_by=request.user,
        )
        
        # TODO: Queue Celery task for actual generation
        
        return Response(GeneratedReportSerializer(report).data, status=201)


class KPIViewSet(viewsets.ModelViewSet):
    queryset = KPI.objects.all()
    serializer_class = KPISerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ar', 'code']


class KPIValueViewSet(viewsets.ModelViewSet):
    queryset = KPIValue.objects.select_related('organization', 'kpi').all()
    serializer_class = KPIValueSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization', 'kpi']
    ordering = ['-period_date']
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest KPI values for organization."""
        org_id = request.query_params.get('organization')
        if not org_id:
            return Response({'error': 'organization required'}, status=400)
        
        kpis = KPI.objects.filter(is_active=True)
        result = []
        
        for kpi in kpis:
            latest_value = KPIValue.objects.filter(
                organization_id=org_id,
                kpi=kpi
            ).order_by('-period_date').first()
            
            result.append({
                'kpi': KPISerializer(kpi).data,
                'value': KPIValueSerializer(latest_value).data if latest_value else None
            })
        
        return Response(result)
