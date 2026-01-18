"""
Notifications app serializers.
"""
from rest_framework import serializers
from .models import NotificationTemplate, Notification, Reminder, Escalation


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['created_at']


class ReminderSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = Reminder
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class EscalationSerializer(serializers.ModelSerializer):
    escalated_from_name = serializers.CharField(source='escalated_from.get_full_name', read_only=True)
    escalated_to_name = serializers.CharField(source='escalated_to.get_full_name', read_only=True)
    
    class Meta:
        model = Escalation
        fields = '__all__'
        read_only_fields = ['escalated_at']
