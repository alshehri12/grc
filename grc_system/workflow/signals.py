"""
Workflow signals for event-driven architecture.
These signals allow loose coupling between the workflow engine
and other parts of the system (notifications, integrations, etc.)
"""
from django.dispatch import Signal

# Fired when a new workflow instance is started
# Arguments: instance (WorkflowInstance), obj (the linked object)
workflow_started = Signal()

# Fired when a workflow step is completed (approved or rejected)
# Arguments: instance (WorkflowInstance), step (WorkflowStep), approval (Approval), decision (str)
step_completed = Signal()

# Fired when a workflow is fully completed (all steps done)
# Arguments: instance (WorkflowInstance)
workflow_completed = Signal()

# Fired when a workflow is escalated due to SLA breach
# Arguments: instance (WorkflowInstance), approval (Approval)
workflow_escalated = Signal()

# Fired when an approval is delegated
# Arguments: approval (Approval), from_user (User), to_user (User)
approval_delegated = Signal()

# Fired when a task is assigned
# Arguments: task (Task), assigned_by (User)
task_assigned = Signal()

# Fired when a task is completed
# Arguments: task (Task), completed_by (User)
task_completed = Signal()
