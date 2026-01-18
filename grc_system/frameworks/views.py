"""
Frameworks app views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import FrameworkTemplate, ControlMapping, RegulatoryRequirement
from .serializers import (
    FrameworkTemplateSerializer, ControlMappingSerializer, RegulatoryRequirementSerializer
)


class FrameworkTemplateViewSet(viewsets.ModelViewSet):
    queryset = FrameworkTemplate.objects.all()
    serializer_class = FrameworkTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ar', 'code']
    
    @action(detail=True, methods=['post'])
    def import_to_organization(self, request, pk=None):
        """Import framework template to organization's control library."""
        from compliance.models import ControlFramework, ControlDomain, Control
        
        template = self.get_object()
        org_id = request.data.get('organization_id')
        
        if not org_id:
            return Response({'error': 'organization_id required'}, status=400)
        
        # Create framework
        framework, created = ControlFramework.objects.get_or_create(
            code=template.code,
            defaults={
                'name': template.name,
                'name_ar': template.name_ar,
                'version': template.version,
                'description': template.description,
                'description_ar': template.description_ar,
            }
        )
        
        if not created:
            return Response({'message': 'Framework already exists', 'framework_id': framework.id})
        
        # Import domains and controls from template_data
        template_data = template.template_data
        for domain_data in template_data.get('domains', []):
            domain = ControlDomain.objects.create(
                framework=framework,
                code=domain_data.get('code'),
                name=domain_data.get('name'),
                name_ar=domain_data.get('name_ar', ''),
                description=domain_data.get('description', ''),
                order=domain_data.get('order', 0),
            )
            
            for control_data in domain_data.get('controls', []):
                Control.objects.create(
                    domain=domain,
                    control_id=control_data.get('control_id'),
                    title=control_data.get('title'),
                    title_ar=control_data.get('title_ar', ''),
                    description=control_data.get('description', ''),
                    description_ar=control_data.get('description_ar', ''),
                    control_type=control_data.get('control_type', 'preventive'),
                    implementation_guidance=control_data.get('implementation_guidance', ''),
                    order=control_data.get('order', 0),
                )
        
        return Response({
            'message': 'Framework imported successfully',
            'framework_id': framework.id
        }, status=201)


class ControlMappingViewSet(viewsets.ModelViewSet):
    queryset = ControlMapping.objects.all()
    serializer_class = ControlMappingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['source_framework', 'target_framework', 'mapping_type']
    
    @action(detail=False, methods=['get'])
    def get_mappings(self, request):
        """Get mappings for a specific control."""
        source_framework = request.query_params.get('source_framework')
        source_control_id = request.query_params.get('source_control_id')
        
        if not source_framework or not source_control_id:
            return Response({'error': 'source_framework and source_control_id required'}, status=400)
        
        mappings = self.queryset.filter(
            source_framework=source_framework,
            source_control_id=source_control_id
        )
        serializer = self.get_serializer(mappings, many=True)
        return Response(serializer.data)


class RegulatoryRequirementViewSet(viewsets.ModelViewSet):
    queryset = RegulatoryRequirement.objects.all()
    serializer_class = RegulatoryRequirementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['framework_code', 'requirement_type']
    search_fields = ['title', 'title_ar', 'requirement_id']
