"""
BCM app views.
"""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from core.audit import AuditedModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    BusinessFunction, BusinessImpactAnalysis, BCPlan, DisasterRecoveryPlan,
    CrisisManagementTeam, CrisisTeamMember, CallTree, CallTreeNode,
    CrisisIncident, BCMTest, BCMTestFinding
)
from .serializers import (
    BusinessFunctionSerializer, BusinessFunctionListSerializer,
    BusinessImpactAnalysisSerializer, BCPlanSerializer, BCPlanListSerializer,
    DisasterRecoveryPlanSerializer, CrisisManagementTeamSerializer,
    CrisisTeamMemberSerializer, CallTreeSerializer, CallTreeNodeSerializer,
    CrisisIncidentSerializer, CrisisIncidentListSerializer,
    BCMTestSerializer, BCMTestListSerializer, BCMTestFindingSerializer
)



class BusinessFunctionViewSet(AuditedModelViewSet):
    queryset = BusinessFunction.objects.select_related(
        'organization', 'department', 'owner', 'parent_function'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'department', 'criticality', 'status']
    search_fields = ['name', 'name_ar', 'function_id']
    ordering_fields = ['criticality', 'name']
    ordering = ['criticality', 'name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BusinessFunctionListSerializer
        return BusinessFunctionSerializer

    @action(detail=False, methods=['get'])
    def capability_analysis(self, request):
        """
        Recovery capability report: what the business needs (BIA RTO/RPO) vs what
        DR plans can deliver and what exercises have proven.
        GET /api/bcm/functions/capability_analysis/?organization=<id>[&criticality=critical,essential]
        """
        from django.conf import settings as dj_settings
        from bcm.utils import capability_analysis
        org_id = request.query_params.get('organization')
        if not org_id:
            return Response({'error': 'organization parameter is required'}, status=400)
        functions = self.queryset.filter(organization_id=org_id, status='active')
        crit = request.query_params.get('criticality')
        if crit:
            functions = functions.filter(criticality__in=crit.split(','))
        interval = dj_settings.GRC_AUTOMATION.get('PLAN_TEST_INTERVAL_DAYS', 365)
        return Response(capability_analysis(org_id, functions, test_interval_days=interval))

    @action(detail=True, methods=['get'])
    def threat_profile(self, request, pk=None):
        """
        BCM risk assessment for a function: risks linked directly plus risks on its
        dependent assets, with current exposure and appetite status.
        """
        from risk.models import Risk
        fn = self.get_object()
        asset_ids = set(fn.related_assets.values_list('id', flat=True))
        bia = fn.bias.filter(status__in=['completed', 'approved']).order_by('-assessment_date').first()
        if bia:
            asset_ids |= set(bia.dependent_assets.values_list('id', flat=True))
        risks = Risk.objects.filter(Q(business_functions=fn) | Q(assets__in=asset_ids)).exclude(status='closed') \
            .select_related('category', 'owner').distinct()
        rows = []
        for r in risks:
            a = r.appetite_status
            rows.append({'id': r.pk, 'risk_id': r.risk_id, 'title': r.title, 'risk_type': r.risk_type,
                         'category': r.category.name if r.category else None, 'status': r.status,
                         'inherent_score': r.inherent_risk_score, 'inherent_level': r.risk_level,
                         'residual_score': r.residual_risk_score, 'residual_level': r.residual_risk_level,
                         'appetite_status': a['status'], 'owner': r.owner.get_full_name() if r.owner else None,
                         'direct': fn.related_risks.filter(pk=r.pk).exists(),
                         'incidents_12m': r.incidents.filter(reported_at__gte=timezone.now() - timedelta(days=365)).count()})
        rows.sort(key=lambda x: -(x['residual_score'] or x['inherent_score']))
        levels = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for row in rows:
            levels[row['residual_level'] or row['inherent_level']] += 1
        return Response({'function': {'id': fn.pk, 'function_id': fn.function_id, 'name': fn.name, 'criticality': fn.criticality},
                         'summary': {'total': len(rows), 'by_level': levels,
                                     'outside_appetite': sum(1 for x in rows if x['appetite_status'] != 'within')},
                         'risks': rows})
    
    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """Get business function hierarchy."""
        org_id = request.query_params.get('organization')
        functions = self.queryset.filter(parent_function__isnull=True)
        if org_id:
            functions = functions.filter(organization_id=org_id)
        
        def build_tree(func):
            return {
                'id': func.id,
                'function_id': func.function_id,
                'name': func.name,
                'name_ar': func.name_ar,
                'criticality': func.criticality,
                'children': [build_tree(child) for child in func.sub_functions.all()]
            }
        
        tree = [build_tree(func) for func in functions]
        return Response(tree)
    
    @action(detail=True, methods=['get'])
    def dependency_analysis(self, request, pk=None):
        """
        Analyze cascading dependency impact for a business function.
        GET /api/bcm/functions/{id}/dependency_analysis/
        """
        from bcm.utils import calculate_dependency_impact
        
        func = self.get_object()
        impact = calculate_dependency_impact(func)
        
        # Get BIA data if available
        bia = func.bias.filter(status__in=['completed', 'approved']).first()
        
        return Response({
            'function': {
                'id': func.id,
                'function_id': func.function_id,
                'name': func.name,
                'criticality': func.criticality,
            },
            'dependencies': {
                'depends_on': [
                    {'id': d.id, 'name': d.name, 'criticality': d.criticality}
                    for d in func.dependent_functions.all()
                ],
                'depended_by': impact['direct_dependents'],
            },
            'cascade_impact': {
                'total_affected_functions': impact['total_affected'],
                'cascade_depth': impact['cascade_depth'],
                'max_affected_criticality': impact['max_criticality'],
            },
            'bia_summary': {
                'rto_hours': bia.rto_hours if bia else None,
                'rpo_hours': bia.rpo_hours if bia else None,
                'mtpd_hours': bia.mtpd_hours if bia else None,
            } if bia else None,
            'risk_assessment': self._assess_function_risk(func, impact)
        })
    
    def _assess_function_risk(self, func, impact):
        """Assess function disruption risk based on criticality and dependencies."""
        criticality_scores = {'critical': 4, 'essential': 3, 'necessary': 2, 'desirable': 1}
        base_score = criticality_scores.get(func.criticality, 1)
        
        # Increase score based on cascade impact
        cascade_multiplier = 1 + (impact['total_affected'] * 0.1)
        
        final_score = min(base_score * cascade_multiplier, 5)
        
        if final_score >= 4:
            risk_level = 'critical'
        elif final_score >= 3:
            risk_level = 'high'
        elif final_score >= 2:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'disruption_risk_score': round(final_score, 1),
            'risk_level': risk_level,
            'recommendation': f'Function has {impact["total_affected"]} dependent functions. '
                            f'Disruption would cause {"significant" if final_score >= 3 else "moderate"} cascade impact.'
        }


class BusinessImpactAnalysisViewSet(AuditedModelViewSet):
    queryset = BusinessImpactAnalysis.objects.select_related(
        'organization', 'business_function', 'assessor', 'approved_by'
    ).all()
    serializer_class = BusinessImpactAnalysisSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization', 'business_function', 'status']
    ordering = ['-assessment_date']
    
    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """
        Get BIA recommendations including RTO, MTPD, and criticality.
        GET /api/bcm/bia/{id}/recommendations/
        """
        bia = self.get_object()
        
        return Response({
            'business_function': bia.business_function.name if bia.business_function else None,
            'current_values': {
                'rto_hours': bia.rto_hours,
                'rpo_hours': bia.rpo_hours,
                'mtpd_hours': bia.mtpd_hours,
            },
            'recommended_values': {
                'rto_hours': bia.recommended_rto,
                'mtpd_hours': bia.recommended_mtpd,
                'criticality': bia.recommended_criticality,
            },
            'impact_progression': {
                '1_hour': bia.impact_1_hour,
                '4_hours': bia.impact_4_hours,
                '8_hours': bia.impact_8_hours,
                '24_hours': bia.impact_24_hours,
                '72_hours': bia.impact_72_hours,
            },
            'validation_warnings': self._get_validation_warnings(bia)
        })
    
    def _get_validation_warnings(self, bia):
        """Generate validation warnings for BIA."""
        warnings = []
        
        if bia.rto_hours and bia.mtpd_hours:
            if bia.rto_hours > bia.mtpd_hours:
                warnings.append({
                    'field': 'rto_hours',
                    'message': 'RTO exceeds MTPD - recovery must happen before maximum tolerable disruption'
                })
        
        if bia.rto_hours and bia.recommended_rto:
            if bia.rto_hours > bia.recommended_rto:
                warnings.append({
                    'field': 'rto_hours',
                    'message': f'RTO ({bia.rto_hours}h) is longer than recommended ({bia.recommended_rto}h) based on impact progression'
                })
        
        if bia.rpo_hours and bia.rto_hours:
            if bia.rpo_hours > bia.rto_hours:
                warnings.append({
                    'field': 'rpo_hours',
                    'message': 'RPO exceeds RTO - data loss point should be before service recovery'
                })
        
        return warnings


class BCPlanViewSet(AuditedModelViewSet):
    queryset = BCPlan.objects.select_related(
        'organization', 'owner', 'approved_by', 'created_by'
    ).prefetch_related('covered_functions').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'status', 'owner']
    search_fields = ['title', 'title_ar', 'plan_id']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BCPlanListSerializer
        return BCPlanSerializer
    
    
    @action(detail=True, methods=['get'])
    def coverage_analysis(self, request, pk=None):
        """
        Analyze BC Plan coverage of critical functions.
        GET /api/bcm/bc-plans/{id}/coverage_analysis/
        """
        from bcm.utils import validate_bc_plan_coverage, plan_test_status
        
        plan = self.get_object()
        coverage = validate_bc_plan_coverage(plan)
        test_status = plan_test_status(plan)
        
        return Response({
            'plan_id': plan.plan_id,
            'title': plan.title,
            'status': plan.status,
            'coverage': coverage,
            'testing': test_status,
            'recommendations': self._get_plan_recommendations(plan, coverage, test_status)
        })
    
    def _get_plan_recommendations(self, plan, coverage, test_status):
        """Generate recommendations for BC Plan."""
        recommendations = []
        
        if not coverage['is_complete']:
            recommendations.append({
                'priority': 'high',
                'type': 'coverage_gap',
                'message': f"Plan is missing {len(coverage['uncovered_critical'])} critical/essential functions",
                'action': 'Add missing functions to plan coverage'
            })
        
        if test_status['needs_testing']:
            recommendations.append({
                'priority': 'medium',
                'type': 'testing_required',
                'message': test_status['recommendation'],
                'action': 'Schedule BC plan test/exercise'
            })
        
        if plan.status == 'draft':
            recommendations.append({
                'priority': 'medium',
                'type': 'approval_pending',
                'message': 'Plan is still in draft status',
                'action': 'Submit plan for review and approval'
            })
        
        if not plan.review_date:
            recommendations.append({
                'priority': 'low',
                'type': 'review_schedule',
                'message': 'No review date scheduled',
                'action': 'Set next review date (recommended: annually)'
            })
        
        return recommendations


class DisasterRecoveryPlanViewSet(AuditedModelViewSet):
    queryset = DisasterRecoveryPlan.objects.select_related(
        'organization', 'bc_plan', 'owner', 'approved_by', 'created_by'
    ).all()
    serializer_class = DisasterRecoveryPlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'status', 'owner']
    search_fields = ['title', 'title_ar', 'plan_id']
    ordering = ['-updated_at']
    


class CrisisManagementTeamViewSet(AuditedModelViewSet):
    queryset = CrisisManagementTeam.objects.prefetch_related('members').all()
    serializer_class = CrisisManagementTeamSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'is_active']
    search_fields = ['name', 'name_ar']


class CrisisTeamMemberViewSet(AuditedModelViewSet):
    queryset = CrisisTeamMember.objects.select_related('team', 'user', 'backup_member').all()
    serializer_class = CrisisTeamMemberSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['team', 'role', 'is_primary']


class CallTreeViewSet(AuditedModelViewSet):
    queryset = CallTree.objects.prefetch_related('nodes').all()
    serializer_class = CallTreeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'is_active']
    search_fields = ['name', 'name_ar']


class CrisisIncidentViewSet(AuditedModelViewSet):
    queryset = CrisisIncident.objects.select_related(
        'organization', 'crisis_team', 'incident_commander',
        'activated_bc_plan', 'activated_dr_plan', 'reported_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'incident_type', 'severity', 'status']
    search_fields = ['title', 'title_ar', 'incident_id']
    ordering = ['-reported_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CrisisIncidentListSerializer
        return CrisisIncidentSerializer
    
    def _can_command(self, incident, user):
        from core.permissions import user_can_approve
        return user_can_approve(user) or user.pk in (incident.incident_commander_id, incident.reported_by_id)

    @action(detail=True, methods=['post'])
    def declare_crisis(self, request, pk=None):
        from django.utils import timezone
        from core.audit import log_action
        incident = self.get_object()
        if not self._can_command(incident, request.user):
            return Response({'error': 'Only the incident commander or a manager can declare a crisis'}, status=403)
        previous = incident.status
        incident.status = 'responding'
        incident.declared_at = timezone.now()
        if not incident.incident_commander_id:
            incident.incident_commander = request.user
        incident.save()
        log_action(request.user, 'update', incident, changes={'status': [previous, 'responding'], 'declared': True}, request=request)
        return Response(CrisisIncidentSerializer(incident).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        from django.utils import timezone
        from core.audit import log_action
        incident = self.get_object()
        if not self._can_command(incident, request.user):
            return Response({'error': 'Only the incident commander or a manager can resolve an incident'}, status=403)
        previous = incident.status
        incident.status = 'resolved'
        incident.resolved_at = timezone.now()
        if request.data.get('lessons_learned'):
            incident.lessons_learned = request.data['lessons_learned']
        incident.save()
        log_action(request.user, 'update', incident, changes={'status': [previous, 'resolved']}, request=request)
        return Response(CrisisIncidentSerializer(incident).data)


class BCMTestViewSet(AuditedModelViewSet):
    queryset = BCMTest.objects.select_related(
        'organization', 'bc_plan', 'dr_plan', 'coordinator', 'created_by'
    ).prefetch_related('participants', 'findings').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'test_type', 'status', 'bc_plan', 'dr_plan']
    search_fields = ['title', 'title_ar', 'test_id']
    ordering = ['-scheduled_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BCMTestListSerializer
        return BCMTestSerializer
    
    def _can_run(self, test, user):
        from core.permissions import user_can_approve
        return user_can_approve(user) or user.pk in (test.coordinator_id, test.created_by_id)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        from django.utils import timezone
        from core.audit import log_action
        test = self.get_object()
        if not self._can_run(test, request.user):
            return Response({'error': 'Only the test coordinator or a manager can start a test'}, status=403)
        if test.status != 'planned':
            return Response({'error': f'Cannot start a test in status {test.status}'}, status=400)
        test.status = 'in_progress'
        test.actual_start = timezone.now()
        test.save()
        log_action(request.user, 'update', test, changes={'status': ['planned', 'in_progress']}, request=request)
        return Response(BCMTestSerializer(test).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        from django.utils import timezone
        from core.audit import log_action
        test = self.get_object()
        if not self._can_run(test, request.user):
            return Response({'error': 'Only the test coordinator or a manager can complete a test'}, status=403)
        if test.status not in ('planned', 'in_progress'):
            return Response({'error': f'Cannot complete a test in status {test.status}'}, status=400)
        previous = test.status
        test.status = 'completed'
        test.actual_end = timezone.now()
        if not test.actual_start:
            test.actual_start = test.actual_end
        test.overall_result = request.data.get('result', test.overall_result)
        test.results_summary = request.data.get('summary', test.results_summary)
        for f in ('achieved_rto_hours', 'achieved_rpo_hours', 'strengths_identified', 'weaknesses_identified', 'lessons_learned'):
            if f in request.data and request.data[f] not in (None, ''):
                setattr(test, f, request.data[f])
        test.save()
        # Keep the tested plans' schedule in sync: last tested today, next test per plan frequency.
        today = test.actual_end.date()
        for plan in (test.bc_plan, test.dr_plan):
            if plan is not None:
                next_due = today + timedelta(days=30 * (plan.test_frequency_months or 12))
                type(plan).objects.filter(pk=plan.pk).update(last_tested_date=today, next_test_date=next_due)
        log_action(request.user, 'update', test, request=request,
                   changes={'status': [previous, 'completed'], 'overall_result': test.overall_result,
                            'achieved_rto_hours': str(test.achieved_rto_hours) if test.achieved_rto_hours is not None else None})
        return Response(BCMTestSerializer(test).data)


class BCMTestFindingViewSet(AuditedModelViewSet):
    queryset = BCMTestFinding.objects.select_related('test', 'assigned_to').all()
    serializer_class = BCMTestFindingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['test', 'severity', 'status', 'assigned_to']
    ordering = ['-severity', '-created_at']
