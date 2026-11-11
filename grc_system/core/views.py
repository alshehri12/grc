"""
Core app views.

Access model:
  - Reference data (organizations, departments, roles, settings, users,
    profiles) is readable by any authenticated user and writable by admins only.
  - Audit logs are read-only, visible to managers and admins.
  - /profiles/me/ lets any user view or update their own profile.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Organization, Department, Role, UserProfile, AuditLog, Setting
from .audit import AuditedModelViewSet, log_action
from .permissions import IsAdminOrReadOnly, IsManagerOrAdmin
from .serializers import (
    UserSerializer, OrganizationSerializer, OrganizationListSerializer,
    DepartmentSerializer, DepartmentListSerializer, RoleSerializer,
    UserProfileSerializer, UserProfileUpdateSerializer, AuditLogSerializer,
    SettingSerializer, CurrentUserSerializer
)


class OrganizationViewSet(AuditedModelViewSet):
    queryset = Organization.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'name_ar', 'code']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        return OrganizationSerializer


class DepartmentViewSet(AuditedModelViewSet):
    queryset = Department.objects.select_related('organization', 'manager', 'parent').all()
    permission_classes = [IsAdminOrReadOnly]
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
                'manager_id': dept.manager_id,
                'children': [build_tree(child) for child in dept.children.all()]
            }

        return Response([build_tree(dept) for dept in queryset])


class RoleViewSet(AuditedModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['role_type', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


class UserProfileViewSet(AuditedModelViewSet):
    queryset = UserProfile.objects.select_related('user', 'organization', 'department').all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'department']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'job_title']

    # Fields a user may change on their own profile (roles/org/department are admin-only).
    SELF_EDITABLE_FIELDS = {
        'first_name_ar', 'last_name_ar', 'phone', 'mobile', 'job_title', 'job_title_ar',
        'avatar', 'preferred_language', 'timezone', 'email_notifications',
    }

    def get_permissions(self):
        if self.action == 'me':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update the current user's own profile."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        if request.method == 'GET':
            return Response(CurrentUserSerializer(request.user).data)

        data = {k: v for k, v in request.data.items() if k in self.SELF_EDITABLE_FIELDS}
        serializer = UserProfileUpdateSerializer(profile, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, 'update', profile, changes={'self_update': list(data.keys())}, request=request)
        return Response(UserProfileSerializer(profile).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsManagerOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'action', 'content_type', 'object_id']
    search_fields = ['object_repr', 'content_type']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']


class SettingViewSet(AuditedModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['organization', 'is_system']
    search_fields = ['key', 'description']

    @action(detail=False, methods=['get'])
    def by_key(self, request):
        key = request.query_params.get('key')
        org_id = request.query_params.get('organization')
        if not key:
            return Response({'error': 'Key parameter required'}, status=400)
        try:
            setting = Setting.objects.get(key=key, organization_id=org_id)
            return Response(SettingSerializer(setting).data)
        except Setting.DoesNotExist:
            return Response({'error': 'Setting not found'}, status=404)


class UserViewSet(AuditedModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['is_active']
