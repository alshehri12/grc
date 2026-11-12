"""
Dashboard app views.
"""
from rest_framework import viewsets, status
from core.audit import AuditedModelViewSet
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


class DashboardWidgetViewSet(AuditedModelViewSet):
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['widget_type', 'data_source', 'is_active']
    search_fields = ['name', 'name_ar']


class DashboardViewSet(AuditedModelViewSet):
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
        
        # Risk levels come from the single configurable risk matrix (risk.utils)
        from risk.utils import get_risk_level, get_risk_thresholds
        by_level = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for likelihood, impact in risks.values_list('inherent_likelihood', 'inherent_impact'):
            by_level[get_risk_level(likelihood * impact, org_id)] += 1

        open_risks = risks.exclude(status__in=['closed', 'pending_approval']).select_related('category')
        appetite_counts = {'within': 0, 'tolerance': 0, 'breach': 0}
        for r in open_risks:
            appetite_counts[r.appetite_status['status']] += 1

        from risk.models import KeyRiskIndicator
        kris = KeyRiskIndicator.objects.filter(is_active=True)
        if org_id:
            kris = kris.filter(organization_id=org_id)
        kri_counts = {'green': 0, 'amber': 0, 'red': 0, 'no_data': 0, 'measurement_overdue': 0}
        for k in kris:
            kri_counts[k.current_status] += 1
            if k.is_measurement_overdue:
                kri_counts['measurement_overdue'] += 1

        risk_summary = {
            'total': risks.count(),
            **by_level,
            'treating': risks.filter(status='treating').count(),
            'by_level': by_level,
            'thresholds': get_risk_thresholds(org_id),
            'appetite': appetite_counts,
            'outside_appetite': appetite_counts['tolerance'] + appetite_counts['breach'],
            'kris': kri_counts,
        }

        # Compliance summary (rate is over applicable controls; partial counts half)
        impls = ControlImplementation.objects.all()
        if org_id:
            impls = impls.filter(organization_id=org_id)

        total_impls = impls.count()
        implemented = impls.filter(status='implemented').count()
        partial = impls.filter(status='partially_implemented').count()
        not_applicable = impls.filter(status='not_applicable').count()
        not_implemented = total_impls - implemented - partial - not_applicable
        applicable = total_impls - not_applicable
        compliance_rate = ((implemented + 0.5 * partial) / applicable * 100) if applicable > 0 else 0

        compliance_summary = {
            'total_controls': total_impls,
            'implemented': implemented,
            'partial': partial,
            'not_implemented': not_implemented,
            'not_applicable': not_applicable,
            'compliance_rate': round(compliance_rate, 1),
            'avg_maturity': round(impls.exclude(status='not_applicable').aggregate(avg=Avg('maturity_level'))['avg'] or 0, 2),
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
        
        from django.conf import settings as dj_settings
        from bcm.utils import capability_analysis, plan_test_status
        capability = None
        if org_id:
            capability = capability_analysis(
                org_id, functions.filter(status='active', criticality__in=['critical', 'essential']),
                test_interval_days=dj_settings.GRC_AUTOMATION.get('PLAN_TEST_INTERVAL_DAYS', 365))['summary']
        live_plans = list(bc_plans.filter(status__in=['approved', 'active'])) + list(dr_plans.filter(status__in=['approved', 'active']))
        tests_overdue = sum(1 for p in live_plans if plan_test_status(p)['overdue'])

        bcm_summary = {
            'bc_plans': bc_plans.count(),
            'bc_plans_active': bc_plans.filter(status='active').count(),
            'dr_plans': dr_plans.count(),
            'dr_plans_active': dr_plans.filter(status='active').count(),
            'business_functions': functions.count(),
            'critical_functions': functions.filter(criticality='critical').count(),
            'tests_completed': bcm_tests.filter(status='completed').count(),
            'tests_planned': bcm_tests.filter(status='planned').count(),
            'plans_test_overdue': tests_overdue,
            'capability': capability,
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


class ReportTemplateViewSet(AuditedModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['report_type', 'output_format', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class GeneratedReportViewSet(AuditedModelViewSet):
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


class KPIViewSet(AuditedModelViewSet):
    queryset = KPI.objects.all()
    serializer_class = KPISerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ar', 'code']


class KPIValueViewSet(AuditedModelViewSet):
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
