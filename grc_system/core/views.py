"""
Core app views.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Organization, Department, Role, UserProfile, AuditLog, Setting
from .serializers import (
    UserSerializer, OrganizationSerializer, OrganizationListSerializer,
    DepartmentSerializer, DepartmentListSerializer, RoleSerializer,
    UserProfileSerializer, UserProfileUpdateSerializer, AuditLogSerializer,
    SettingSerializer, CurrentUserSerializer
)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organization management.
    """
    queryset = Organization.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'name_ar', 'code']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        return OrganizationSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Department management.
    """
    queryset = Department.objects.select_related('organization', 'manager', 'parent').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'is_active', 'parent']
    search_fields = ['name', 'name_ar', 'code']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DepartmentListSerializer
        return DepartmentSerializer
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get department hierarchy as tree."""
        org_id = request.query_params.get('organization')
        queryset = self.queryset.filter(parent__isnull=True)
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        
        def build_tree(dept):
            return {
                'id': dept.id,
                'name': dept.name,
                'name_ar': dept.name_ar,
                'code': dept.code,
                'children': [build_tree(child) for child in dept.children.all()]
            }
        
        tree = [build_tree(dept) for dept in queryset]
        return Response(tree)


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Role management.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['role_type', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UserProfile management.
    """
    queryset = UserProfile.objects.select_related('user', 'organization', 'department').all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'department']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'job_title']
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's profile."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'GET':
            serializer = CurrentUserSerializer(request.user)
            return Response(serializer.data)
        
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(profile).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AuditLog (read-only).
    """
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'action', 'content_type']
    search_fields = ['object_repr', 'content_type']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']


class SettingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Settings management.
    """
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'is_system']
    search_fields = ['key', 'description']
    
    @action(detail=False, methods=['get'])
    def by_key(self, request):
        """Get setting by key."""
        key = request.query_params.get('key')
        org_id = request.query_params.get('organization')
        
        if not key:
            return Response({'error': 'Key parameter required'}, status=400)
        
        try:
            setting = Setting.objects.get(key=key, organization_id=org_id)
            return Response(SettingSerializer(setting).data)
        except Setting.DoesNotExist:
            return Response({'error': 'Setting not found'}, status=404)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User management.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['is_active']
