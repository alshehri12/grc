"""
Core app serializers.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Organization, Department, Role, UserProfile, AuditLog, Setting


class UserSerializer(serializers.ModelSerializer):
    """User serializer with profile info."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active']
        read_only_fields = ['id']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class OrganizationSerializer(serializers.ModelSerializer):
    """Organization serializer."""
    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class OrganizationListSerializer(serializers.ModelSerializer):
    """Lightweight organization serializer for lists."""
    class Meta:
        model = Organization
        fields = ['id', 'name', 'name_ar', 'code', 'is_active']


class DepartmentSerializer(serializers.ModelSerializer):
    """Department serializer."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class DepartmentListSerializer(serializers.ModelSerializer):
    """Lightweight department serializer for lists."""
    class Meta:
        model = Department
        fields = ['id', 'name', 'name_ar', 'code', 'organization', 'is_active']


class RoleSerializer(serializers.ModelSerializer):
    """Role serializer."""
    class Meta:
        model = Role
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer."""
    user = UserSerializer(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    roles_list = RoleSerializer(source='roles', many=True, read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """User profile update serializer."""
    class Meta:
        model = UserProfile
        exclude = ['user', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    """Audit log serializer."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['timestamp']


class SettingSerializer(serializers.ModelSerializer):
    """Setting serializer."""
    class Meta:
        model = Setting
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CurrentUserSerializer(serializers.ModelSerializer):
    """Current user with full profile and role info."""
    profile = UserProfileSerializer(read_only=True)
    is_author = serializers.SerializerMethodField()
    is_manager = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_superuser',
                  'profile', 'is_author', 'is_manager', 'is_admin', 'department', 'roles']
    
    def get_is_author(self, obj):
        try:
            return obj.profile.roles.filter(code='author').exists()
        except Exception:
            return False
    
    def get_is_manager(self, obj):
        try:
            return obj.profile.roles.filter(code='manager').exists()
        except Exception:
            return False
    
    def get_is_admin(self, obj):
        if obj.is_superuser:
            return True
        try:
            return obj.profile.roles.filter(code='admin').exists()
        except Exception:
            return False
    
    def get_department(self, obj):
        try:
            if obj.profile.department:
                return {
                    'id': obj.profile.department.id,
                    'name': obj.profile.department.name,
                    'name_ar': obj.profile.department.name_ar,
                    'code': obj.profile.department.code,
                    'manager_id': obj.profile.department.manager_id
                }
        except Exception:
            pass
        return None
    
    def get_roles(self, obj):
        try:
            return list(obj.profile.roles.values_list('code', flat=True))
        except Exception:
            return []
