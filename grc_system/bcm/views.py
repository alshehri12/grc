"""
BCM app views.
"""
import json
import time
from rest_framework import viewsets, status
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

# region agent log
DEBUG_LOG_PATH = r'c:\Users\aalshehre\GRC\grc_system\grc\.cursor\debug.log'
def debug_log(location, message, data, hypothesis_id):
    try:
        log_entry = json.dumps({'location': location, 'message': message, 'data': data, 'timestamp': int(time.time() * 1000), 'sessionId': 'debug-session', 'hypothesisId': hypothesis_id})
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except: pass
# endregion


class BusinessFunctionViewSet(viewsets.ModelViewSet):
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


class BusinessImpactAnalysisViewSet(viewsets.ModelViewSet):
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


class BCPlanViewSet(viewsets.ModelViewSet):
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
    
    # region agent log
    def create(self, request, *args, **kwargs):
        debug_log('BCPlanViewSet.create:entry', 'Create BC plan request received', {'request_data': request.data}, 'BCPLAN')
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            debug_log('BCPlanViewSet.create:validation_error', 'Serializer validation failed', {'errors': serializer.errors}, 'BCPLAN')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        debug_log('BCPlanViewSet.create:validation_passed', 'Serializer validation passed', {}, 'BCPLAN')
        try:
            self.perform_create(serializer)
            debug_log('BCPlanViewSet.create:success', 'BC plan created successfully', {'id': serializer.data.get('id')}, 'BCPLAN')
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            debug_log('BCPlanViewSet.create:exception', 'Exception during BC plan creation', {'error': str(e)}, 'BCPLAN')
            raise
    # endregion
    
    @action(detail=True, methods=['get'])
    def coverage_analysis(self, request, pk=None):
        """
        Analyze BC Plan coverage of critical functions.
        GET /api/bcm/bc-plans/{id}/coverage_analysis/
        """
        from bcm.utils import validate_bc_plan_coverage, check_plan_test_status
        
        plan = self.get_object()
        coverage = validate_bc_plan_coverage(plan)
        test_status = check_plan_test_status(plan)
        
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


class DisasterRecoveryPlanViewSet(viewsets.ModelViewSet):
    queryset = DisasterRecoveryPlan.objects.select_related(
        'organization', 'bc_plan', 'owner', 'approved_by', 'created_by'
    ).all()
    serializer_class = DisasterRecoveryPlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'status', 'owner']
    search_fields = ['title', 'title_ar', 'plan_id']
    ordering = ['-updated_at']
    
    # region agent log
    def create(self, request, *args, **kwargs):
        debug_log('DRPlanViewSet.create:entry', 'Create DR plan request received', {'request_data': request.data}, 'DRPLAN')
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            debug_log('DRPlanViewSet.create:validation_error', 'Serializer validation failed', {'errors': serializer.errors}, 'DRPLAN')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        debug_log('DRPlanViewSet.create:validation_passed', 'Serializer validation passed', {}, 'DRPLAN')
        try:
            self.perform_create(serializer)
            debug_log('DRPlanViewSet.create:success', 'DR plan created successfully', {'id': serializer.data.get('id')}, 'DRPLAN')
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            debug_log('DRPlanViewSet.create:exception', 'Exception during DR plan creation', {'error': str(e)}, 'DRPLAN')
            raise
    # endregion


class CrisisManagementTeamViewSet(viewsets.ModelViewSet):
    queryset = CrisisManagementTeam.objects.prefetch_related('members').all()
    serializer_class = CrisisManagementTeamSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'is_active']
    search_fields = ['name', 'name_ar']


class CrisisTeamMemberViewSet(viewsets.ModelViewSet):
    queryset = CrisisTeamMember.objects.select_related('team', 'user', 'backup_member').all()
    serializer_class = CrisisTeamMemberSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['team', 'role', 'is_primary']


class CallTreeViewSet(viewsets.ModelViewSet):
    queryset = CallTree.objects.prefetch_related('nodes').all()
    serializer_class = CallTreeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'is_active']
    search_fields = ['name', 'name_ar']


class CrisisIncidentViewSet(viewsets.ModelViewSet):
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
    
    @action(detail=True, methods=['post'])
    def declare_crisis(self, request, pk=None):
        from django.utils import timezone
        incident = self.get_object()
        incident.status = 'responding'
        incident.declared_at = timezone.now()
        incident.save()
        return Response(CrisisIncidentSerializer(incident).data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        from django.utils import timezone
        incident = self.get_object()
        incident.status = 'resolved'
        incident.resolved_at = timezone.now()
        incident.save()
        return Response(CrisisIncidentSerializer(incident).data)


class BCMTestViewSet(viewsets.ModelViewSet):
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
    
    def create(self, request, *args, **kwargs):
        # #region agent log
        import json
        from django.utils import timezone
        log_entry = {
            "location": "BCMTestViewSet.create:entry",
            "message": "Create BCM test request received",
            "data": {"request_data": request.data},
            "timestamp": timezone.now().timestamp() * 1000,
            "sessionId": "debug-session",
            "hypothesisId": "BCMTEST"
        }
        with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        # #endregion
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # #region agent log
            log_entry = {
                "location": "BCMTestViewSet.create:validation_error",
                "message": "Serializer validation failed",
                "data": {"errors": serializer.errors, "data": serializer.initial_data},
                "timestamp": timezone.now().timestamp() * 1000,
                "sessionId": "debug-session",
                "hypothesisId": "BCMTEST"
            }
            with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            # #endregion
            return Response(serializer.errors, status=400)
        # #region agent log
        log_entry = {
            "location": "BCMTestViewSet.create:validation_passed",
            "message": "Serializer validation passed",
            "data": {},
            "timestamp": timezone.now().timestamp() * 1000,
            "sessionId": "debug-session",
            "hypothesisId": "BCMTEST"
        }
        with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        # #endregion
        test = serializer.save()
        # #region agent log
        log_entry = {
            "location": "BCMTestViewSet.create:success",
            "message": "BCM test created successfully",
            "data": {"id": test.id},
            "timestamp": timezone.now().timestamp() * 1000,
            "sessionId": "debug-session",
            "hypothesisId": "BCMTEST"
        }
        with open('c:\\Users\\aalshehre\\GRC\\grc_system\\grc\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        # #endregion
        return Response(self.get_serializer(test).data, status=201)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        from django.utils import timezone
        test = self.get_object()
        test.status = 'in_progress'
        test.actual_start = timezone.now()
        test.save()
        return Response(BCMTestSerializer(test).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        from django.utils import timezone
        test = self.get_object()
        test.status = 'completed'
        test.actual_end = timezone.now()
        test.overall_result = request.data.get('result', '')
        test.results_summary = request.data.get('summary', '')
        test.save()
        return Response(BCMTestSerializer(test).data)


class BCMTestFindingViewSet(viewsets.ModelViewSet):
    queryset = BCMTestFinding.objects.select_related('test', 'assigned_to').all()
    serializer_class = BCMTestFindingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['test', 'severity', 'status', 'assigned_to']
    ordering = ['-severity', '-created_at']
