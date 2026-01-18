"""
BCM app views.
"""
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


class BusinessImpactAnalysisViewSet(viewsets.ModelViewSet):
    queryset = BusinessImpactAnalysis.objects.select_related(
        'organization', 'business_function', 'assessor', 'approved_by'
    ).all()
    serializer_class = BusinessImpactAnalysisSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization', 'business_function', 'status']
    ordering = ['-assessment_date']


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


class DisasterRecoveryPlanViewSet(viewsets.ModelViewSet):
    queryset = DisasterRecoveryPlan.objects.select_related(
        'organization', 'bc_plan', 'owner', 'approved_by', 'created_by'
    ).all()
    serializer_class = DisasterRecoveryPlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'status', 'owner']
    search_fields = ['title', 'title_ar', 'plan_id']
    ordering = ['-updated_at']


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
