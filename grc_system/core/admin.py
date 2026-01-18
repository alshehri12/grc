"""
Core app admin configuration.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Organization, Department, Role, UserProfile, AuditLog, Setting


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'get_organization']
    list_select_related = ['profile']
    
    def get_organization(self, obj):
        try:
            return obj.profile.organization
        except UserProfile.DoesNotExist:
            return None
    get_organization.short_description = 'Organization'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'name_ar', 'code', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'organization', 'manager', 'is_active']
    list_filter = ['organization', 'is_active']
    search_fields = ['name', 'name_ar', 'code']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['manager', 'parent']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'role_type', 'is_active']
    list_filter = ['role_type', 'is_active']
    search_fields = ['name', 'name_ar', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'content_type', 'object_repr', 'timestamp']
    list_filter = ['action', 'content_type', 'timestamp']
    search_fields = ['object_repr', 'content_type']
    readonly_fields = ['user', 'action', 'content_type', 'object_id', 'object_repr', 'changes', 'ip_address', 'user_agent', 'timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'organization', 'value_type', 'is_system', 'updated_at']
    list_filter = ['organization', 'value_type', 'is_system']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']
