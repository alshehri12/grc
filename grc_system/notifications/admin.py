from django.contrib import admin
from .models import NotificationTemplate, Notification, Reminder, Escalation


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'event_type', 'channel', 'is_active']
    list_filter = ['event_type', 'channel', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'channel', 'status', 'priority', 'created_at']
    list_filter = ['status', 'channel', 'priority', 'created_at']
    search_fields = ['subject', 'recipient__username']
    date_hierarchy = 'created_at'


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'frequency', 'status', 'scheduled_date', 'last_sent_at']
    list_filter = ['frequency', 'status']
    search_fields = ['title', 'title_ar']


@admin.register(Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ['object_title', 'level', 'status', 'escalated_from', 'escalated_to', 'escalated_at']
    list_filter = ['status', 'level', 'escalated_at']
    date_hierarchy = 'escalated_at'
