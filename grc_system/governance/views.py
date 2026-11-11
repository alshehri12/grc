"""
Governance app views.

Visibility rules (applied to policies, procedures and documents):
  - Admin: everything.
  - Manager: everything that is in force, plus pending items from their
    department, plus their own items.
  - Everyone else: everything that is in force, plus their own items.

State changes (submit / approve / publish / retire) are explicit actions
with role checks and an audit trail; nobody can approve their own content.
"""
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from core.audit import AuditedModelViewSet, log_action
from core.permissions import (
    IsOwnerOrManagerOrAdmin, user_is_admin, user_is_manager, user_can_approve,
    get_user_department, is_owner_of,
)
from .models import PolicyCategory, Policy, PolicyVersion, PolicyAcknowledgment, Procedure, Document
from .serializers import (
    PolicyCategorySerializer, PolicySerializer, PolicyListSerializer,
    PolicyVersionSerializer, PolicyAcknowledgmentSerializer,
    ProcedureSerializer, ProcedureListSerializer,
    DocumentSerializer, DocumentListSerializer
)

# Statuses that mean "in force / visible to the whole organization".
IN_FORCE_STATUSES = ('approved', 'published')
PENDING_STATUSES = ('pending_review', 'pending_approval')
DOCUMENT_VISIBLE_STATUSES = ('active', 'under_review')


def scope_for_user(qs, user, visible_statuses, pending_statuses=()):
    """Apply the governance visibility rules to a queryset."""
    if not user.is_authenticated:
        return qs.filter(status__in=visible_statuses)
    if user_is_admin(user):
        return qs
    visible = Q(status__in=visible_statuses) | Q(created_by=user) | Q(owner=user)
    if user_is_manager(user):
        dept = get_user_department(user)
        if dept:
            visible |= Q(department=dept)
            if pending_statuses:
                visible |= Q(status__in=pending_statuses, created_by__profile__department=dept)
    return qs.filter(visible).distinct()


class GovernanceContentViewSet(AuditedModelViewSet):
    """Shared behaviour for policies, procedures and documents."""
    permission_classes = [IsOwnerOrManagerOrAdmin]
    visible_statuses = IN_FORCE_STATUSES
    pending_statuses = PENDING_STATUSES
    list_serializer_class = None
    detail_serializer_class = None

    def get_queryset(self):
        return scope_for_user(super().get_queryset(), self.request.user, self.visible_statuses, self.pending_statuses)

    def get_serializer_class(self):
        if self.action == 'list' and self.list_serializer_class:
            return self.list_serializer_class
        return self.detail_serializer_class

    def perform_create(self, serializer):
        serializer.validated_data['created_by'] = self.request.user
        if not serializer.validated_data.get('owner'):
            serializer.validated_data['owner'] = self.request.user
        return super().perform_create(serializer)

    def _transition(self, request, obj, new_status, allowed_from, extra=None):
        previous = obj.status
        if previous not in allowed_from:
            return Response({'error': f'Cannot change status from {previous} to {new_status}'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = new_status
        for k, v in (extra or {}).items():
            setattr(obj, k, v)
        obj.save()
        log_action(request.user, 'update', obj, changes={'status': [previous, new_status]}, request=request)
        return Response({'status': new_status})


class PolicyCategoryViewSet(AuditedModelViewSet):
    queryset = PolicyCategory.objects.all()
    serializer_class = PolicyCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'name_ar', 'code']


class PolicyViewSet(GovernanceContentViewSet):
    queryset = Policy.objects.select_related(
        'organization', 'category', 'owner', 'department', 'approved_by', 'created_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'category', 'status', 'classification', 'owner', 'department']
    search_fields = ['title', 'title_ar', 'policy_id']
    ordering_fields = ['updated_at', 'effective_date', 'review_date']
    ordering = ['-updated_at']
    list_serializer_class = PolicyListSerializer
    detail_serializer_class = PolicySerializer

    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        policy = self.get_object()
        if not (is_owner_of(request.user, policy) or user_can_approve(request.user)):
            return Response({'error': 'Only the policy owner can submit it for review'}, status=status.HTTP_403_FORBIDDEN)
        return self._transition(request, policy, 'pending_review', allowed_from=('draft',))

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        policy = self.get_object()
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)
        if is_owner_of(request.user, policy):
            return Response({'error': 'You cannot approve your own policy'}, status=status.HTTP_403_FORBIDDEN)
        return self._transition(
            request, policy, 'approved', allowed_from=PENDING_STATUSES,
            extra={'approved_by': request.user, 'approved_date': timezone.now().date()},
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        policy = self.get_object()
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)
        if policy.status != 'approved':
            return Response({'error': 'Policy must be approved first'}, status=status.HTTP_400_BAD_REQUEST)
        extra = {}
        if not policy.effective_date:
            extra['effective_date'] = timezone.now().date()
        return self._transition(request, policy, 'published', allowed_from=('approved',), extra=extra)

    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        policy = self.get_object()
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)
        return self._transition(request, policy, 'retired', allowed_from=('approved', 'published'))

    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        policies = self.get_queryset().filter(status='pending_review')
        return Response(PolicyListSerializer(policies, many=True).data)

    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """Policies awaiting the current manager's approval."""
        user = request.user
        if not user_can_approve(user):
            return Response({'error': 'Only managers can view pending approvals'}, status=status.HTTP_403_FORBIDDEN)
        policies = self.get_queryset().filter(status='pending_approval').exclude(created_by=user)
        if not user_is_admin(user):
            dept = get_user_department(user)
            policies = policies.filter(Q(department=dept) | Q(created_by__profile__department=dept)) if dept else policies.none()
        return Response(PolicyListSerializer(policies, many=True).data)


class PolicyVersionViewSet(AuditedModelViewSet):
    queryset = PolicyVersion.objects.select_related('policy', 'created_by').all()
    serializer_class = PolicyVersionSerializer
    permission_classes = [IsOwnerOrManagerOrAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['policy']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        visible_policies = scope_for_user(Policy.objects.all(), self.request.user, IN_FORCE_STATUSES, PENDING_STATUSES)
        return qs.filter(policy__in=visible_policies)

    def perform_create(self, serializer):
        serializer.validated_data.setdefault('created_by', self.request.user)
        return super().perform_create(serializer)


class PolicyAcknowledgmentViewSet(AuditedModelViewSet):
    queryset = PolicyAcknowledgment.objects.select_related('policy', 'user').all()
    serializer_class = PolicyAcknowledgmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['policy', 'user']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        if user_can_approve(self.request.user):
            return qs
        return qs.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        return self.acknowledge(request)

    @action(detail=False, methods=['post'])
    def acknowledge(self, request):
        """Acknowledge a policy on behalf of the current user."""
        policy_id = request.data.get('policy_id') or request.data.get('policy')
        policy = Policy.objects.filter(id=policy_id).first()
        if not policy:
            return Response({'error': 'Policy not found'}, status=status.HTTP_404_NOT_FOUND)
        if policy.status not in IN_FORCE_STATUSES:
            return Response({'error': 'Only approved or published policies can be acknowledged'},
                            status=status.HTTP_400_BAD_REQUEST)
        ack, created = PolicyAcknowledgment.objects.get_or_create(
            policy=policy, user=request.user, version=policy.version,
            defaults={'ip_address': request.META.get('REMOTE_ADDR')},
        )
        if not created:
            return Response({'message': 'Already acknowledged'}, status=status.HTTP_200_OK)
        log_action(request.user, 'submit', policy, changes={'acknowledged_version': policy.version}, request=request)
        return Response(PolicyAcknowledgmentSerializer(ack).data, status=status.HTTP_201_CREATED)


class ProcedureViewSet(GovernanceContentViewSet):
    queryset = Procedure.objects.select_related(
        'organization', 'policy', 'owner', 'department', 'created_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'policy', 'status', 'owner', 'department']
    search_fields = ['title', 'title_ar', 'procedure_id']
    ordering_fields = ['updated_at', 'effective_date']
    ordering = ['-updated_at']
    list_serializer_class = ProcedureListSerializer
    detail_serializer_class = ProcedureSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        procedure = self.get_object()
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)
        return self._transition(request, procedure, 'published', allowed_from=('approved',))

    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        procedure = self.get_object()
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)
        return self._transition(request, procedure, 'retired', allowed_from=('approved', 'published'))


class DocumentViewSet(GovernanceContentViewSet):
    queryset = Document.objects.select_related(
        'organization', 'owner', 'department', 'created_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'document_type', 'status', 'classification', 'department']
    search_fields = ['title', 'title_ar', 'document_id']
    ordering_fields = ['updated_at', 'effective_date']
    ordering = ['-updated_at']
    list_serializer_class = DocumentListSerializer
    detail_serializer_class = DocumentSerializer
    visible_statuses = DOCUMENT_VISIBLE_STATUSES
    pending_statuses = ()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user_is_admin(user):
            return qs
        # Restricted documents are limited to the owning department, managers and the allowed roles.
        try:
            role_ids = list(user.profile.roles.values_list('id', flat=True))
            dept = user.profile.department
        except Exception:
            role_ids, dept = [], None
        restricted = Q(classification='restricted') & ~Q(created_by=user) & ~Q(owner=user)
        allowed = Q(allowed_roles__in=role_ids)
        if dept:
            allowed |= Q(department=dept)
        if user_is_manager(user):
            allowed |= Q(pk__isnull=False)
        return qs.exclude(restricted & ~allowed).distinct()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        document = self.get_object()
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)
        if is_owner_of(request.user, document) and not user_is_admin(request.user):
            return Response({'error': 'You cannot activate your own document'}, status=status.HTTP_403_FORBIDDEN)
        extra = {} if document.effective_date else {'effective_date': timezone.now().date()}
        return self._transition(request, document, 'active', allowed_from=('draft', 'under_review'), extra=extra)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        document = self.get_object()
        if not user_can_approve(request.user):
            return Response({'error': 'Manager or administrator role required'}, status=status.HTTP_403_FORBIDDEN)
        return self._transition(request, document, 'archived', allowed_from=('active', 'under_review', 'draft'))
