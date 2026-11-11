"""
Role helpers and DRF permission classes shared by all GRC apps.

Roles are stored on UserProfile.roles (core.Role, matched by code):
  - admin   : full system access (also granted to Django superusers)
  - manager : can approve content and manage their department's items
  - author  : can create/edit content; everything they create needs approval
"""
from rest_framework import permissions


def _role_codes(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return set()
    cached = getattr(user, '_grc_role_codes', None)
    if cached is None:
        try:
            cached = set(user.profile.roles.filter(is_active=True).values_list('code', flat=True))
        except Exception:
            cached = set()
        user._grc_role_codes = cached
    return cached


def user_is_admin(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return bool(user.is_superuser) or 'admin' in _role_codes(user)


def user_is_manager(user):
    return 'manager' in _role_codes(user)


def user_is_author(user):
    return 'author' in _role_codes(user)


def user_can_approve(user):
    """Managers and admins may act as approvers."""
    return user_is_admin(user) or user_is_manager(user)


def get_user_department(user):
    try:
        return user.profile.department
    except Exception:
        return None


def get_user_organization(user):
    try:
        return user.profile.organization
    except Exception:
        return None


def is_owner_of(user, obj):
    """True when the user created, owns, or requested the object."""
    if not user or not obj:
        return False
    for attr in ('created_by_id', 'owner_id', 'requested_by_id', 'submitted_by_id'):
        if getattr(obj, attr, None) == user.pk:
            return True
    return False


# --------------------------------------------------------------------------- #
# DRF permission classes
# --------------------------------------------------------------------------- #
class IsAdminRole(permissions.BasePermission):
    """Only admins (role or superuser)."""
    message = 'Administrator role required.'

    def has_permission(self, request, view):
        return user_is_admin(request.user)


class IsAdminOrReadOnly(permissions.BasePermission):
    """Authenticated users may read; only admins may write."""
    message = 'Administrator role required to modify this resource.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return user_is_admin(request.user)


class IsManagerOrAdmin(permissions.BasePermission):
    """Managers and admins only."""
    message = 'Manager or administrator role required.'

    def has_permission(self, request, view):
        return user_can_approve(request.user)


class IsManagerOrAdminOrReadOnly(permissions.BasePermission):
    """Authenticated users may read; managers/admins may write."""
    message = 'Manager or administrator role required to modify this resource.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return user_can_approve(request.user)


class IsOwnerOrManagerOrAdmin(permissions.BasePermission):
    """
    Object-level: read for everyone authenticated; write only for the
    creator/owner of the object, managers, or admins.
    """
    message = 'You may only modify items you own.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return user_can_approve(request.user) or is_owner_of(request.user, obj)
