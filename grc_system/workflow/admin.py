from django.contrib import admin
from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, Approval, Task


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'workflow_type', 'is_active']
    list_filter = ['workflow_type', 'is_active']
    search_fields = ['name', 'name_ar', 'code']


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ['template', 'order', 'name', 'step_type']
    list_filter = ['template', 'step_type']


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ['template', 'object_title', 'status', 'current_step', 'initiated_by', 'started_at']
    list_filter = ['status', 'template']
    search_fields = ['object_title']


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ['workflow_instance', 'step', 'assignee', 'status', 'created_at']
    list_filter = ['status']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task_type', 'priority', 'status', 'assigned_to', 'due_date']
    list_filter = ['status', 'priority', 'task_type']
    search_fields = ['title', 'title_ar']
