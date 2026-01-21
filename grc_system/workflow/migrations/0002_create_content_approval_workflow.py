# Generated migration to create content approval workflow template

from django.db import migrations


def create_workflow_template(apps, schema_editor):
    WorkflowTemplate = apps.get_model('workflow', 'WorkflowTemplate')
    WorkflowStep = apps.get_model('workflow', 'WorkflowStep')
    
    # Create Content Approval Workflow Template
    template, created = WorkflowTemplate.objects.get_or_create(
        code='content-approval',
        defaults={
            'name': 'Content Approval',
            'name_ar': 'اعتماد المحتوى',
            'workflow_type': 'approval',
            'description': 'Manager approval workflow for all GRC content created by authors',
            'description_ar': 'سير عمل اعتماد المدير لجميع محتوى GRC الذي أنشأه المؤلفون',
            'applicable_models': [
                'governance.policy', 'governance.procedure',
                'risk.risk', 
                'bcm.businessfunction', 'bcm.bcplan', 'bcm.disasterrecoveryplan', 'bcm.bcmtest',
                'compliance.audit'
            ],
            'default_sla_days': 3,
            'escalation_enabled': True,
            'escalation_days': 2,
            'is_active': True
        }
    )
    
    if created:
        # Create the Manager Approval step
        WorkflowStep.objects.create(
            template=template,
            order=1,
            name='Manager Approval',
            name_ar='اعتماد المدير',
            step_type='approval',
            assignee_type='manager',
            sla_days=3,
            is_required=True,
            allow_delegation=True,
            instructions='Please review and approve this content created by a team member. Verify the content is accurate and complies with organizational standards.',
            instructions_ar='يرجى مراجعة واعتماد هذا المحتوى الذي أنشأه أحد أعضاء الفريق. تحقق من دقة المحتوى وامتثاله للمعايير التنظيمية.'
        )


def remove_workflow_template(apps, schema_editor):
    WorkflowTemplate = apps.get_model('workflow', 'WorkflowTemplate')
    WorkflowTemplate.objects.filter(code='content-approval').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_workflow_template, remove_workflow_template),
    ]
