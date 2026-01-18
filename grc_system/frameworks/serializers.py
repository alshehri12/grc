"""
Frameworks app serializers.
"""
from rest_framework import serializers
from .models import FrameworkTemplate, ControlMapping, RegulatoryRequirement


class FrameworkTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrameworkTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ControlMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlMapping
        fields = '__all__'


class RegulatoryRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulatoryRequirement
        fields = '__all__'
