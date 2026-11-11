from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workflow"

    def ready(self):
        # Apply approved/rejected statuses to GRC content when a workflow ends.
        from .signals import workflow_completed
        from .content import handle_workflow_completed
        workflow_completed.connect(handle_workflow_completed, dispatch_uid='grc-content-workflow-completed')
