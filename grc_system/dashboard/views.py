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
        from bcm.models import BCPlan, DisasterRecoveryPlan, BusinessFunction, BCMTest
        
        org_id = request.query_params.get('organization')
        
        # Risk summary with proper level calculation
        risks = Risk.objects.all()
        if org_id:
            risks = risks.filter(organization_id=org_id)
        
        # Calculate risk levels properly
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        
        for risk in risks:
            score = risk.inherent_likelihood * risk.inherent_impact
            if score >= 20:
                critical_count += 1
            elif score >= 12:
                high_count += 1
            elif score >= 6:
                medium_count += 1
            else:
                low_count += 1
        
        risk_summary = {
            'total': risks.count(),
            'critical': critical_count,
            'high': high_count,
            'medium': medium_count,
            'low': low_count,
            'treating': risks.filter(status='treating').count(),
            'by_level': {
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
            }
        }
        
        # Compliance summary
        impls = ControlImplementation.objects.all()
        if org_id:
            impls = impls.filter(organization_id=org_id)
        
        total_impls = impls.count()
        implemented = impls.filter(status='implemented').count()
        partial = impls.filter(status='partial').count()
        not_implemented = impls.filter(status__in=['not_implemented', 'not_applicable']).count()
        compliance_rate = (implemented / total_impls * 100) if total_impls > 0 else 0
        
        compliance_summary = {
            'total_controls': total_impls,
            'implemented': implemented,
            'partial': partial,
            'not_implemented': not_implemented,
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
        
        # Policies (Governance)
        policies = Policy.objects.all()
        if org_id:
            policies = policies.filter(organization_id=org_id)
        
        policies_summary = {
            'total': policies.count(),
            'published': policies.filter(status='published').count(),
            'draft': policies.filter(status='draft').count(),
            'pending_review': policies.filter(status='pending_review').count(),
            'expiring_soon': policies.filter(
                review_date__lte=timezone.now().date() + timezone.timedelta(days=30)
            ).count(),
        }
        
        # BCM Summary
        bc_plans = BCPlan.objects.all()
        dr_plans = DisasterRecoveryPlan.objects.all()
        functions = BusinessFunction.objects.all()
        bcm_tests = BCMTest.objects.all()
        
        if org_id:
            bc_plans = bc_plans.filter(organization_id=org_id)
            dr_plans = dr_plans.filter(organization_id=org_id)
            functions = functions.filter(organization_id=org_id)
            bcm_tests = bcm_tests.filter(organization_id=org_id)
        
        bcm_summary = {
            'bc_plans': bc_plans.count(),
            'bc_plans_active': bc_plans.filter(status='active').count(),
            'dr_plans': dr_plans.count(),
            'dr_plans_active': dr_plans.filter(status='active').count(),
            'business_functions': functions.count(),
            'critical_functions': functions.filter(criticality='critical').count(),
            'tests_completed': bcm_tests.filter(status='completed').count(),
            'tests_planned': bcm_tests.filter(status='planned').count(),
        }
        
        # Audits summary
        audits = Audit.objects.all()
        if org_id:
            audits = audits.filter(organization_id=org_id)
        
        audits_summary = {
            'total': audits.count(),
            'planned': audits.filter(status='planned').count(),
            'in_progress': audits.filter(status='in_progress').count(),
            'completed': audits.filter(status='completed').count(),
        }
        
        return Response({
            'risks': risk_summary,
            'compliance': compliance_summary,
            'findings': findings_summary,
            'tasks': tasks_summary,
            'policies': policies_summary,
            'bcm': bcm_summary,
            'audits': audits_summary,
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
