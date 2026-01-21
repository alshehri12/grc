# Generated migration to create default departments

from django.db import migrations


def create_departments(apps, schema_editor):
    Organization = apps.get_model('core', 'Organization')
    Department = apps.get_model('core', 'Department')
    
    # Get the first organization (should exist from initial setup)
    org = Organization.objects.first()
    if not org:
        return  # No organization, skip department creation
    
    departments = [
        {'name': 'Human Resources', 'name_ar': 'الموارد البشرية', 'code': 'HR'},
        {'name': 'Finance', 'name_ar': 'المالية', 'code': 'FIN'},
        {'name': 'Information Technology', 'name_ar': 'تقنية المعلومات', 'code': 'IT'},
        {'name': 'Operations', 'name_ar': 'العمليات', 'code': 'OPS'},
        {'name': 'Legal', 'name_ar': 'الشؤون القانونية', 'code': 'LEGAL'},
        {'name': 'Risk Management', 'name_ar': 'إدارة المخاطر', 'code': 'RISK'},
        {'name': 'Compliance', 'name_ar': 'الامتثال', 'code': 'COMP'},
    ]
    
    for dept_data in departments:
        Department.objects.get_or_create(
            organization=org,
            code=dept_data['code'],
            defaults={
                'name': dept_data['name'],
                'name_ar': dept_data['name_ar'],
                'description': f"{dept_data['name']} Department",
                'description_ar': f"إدارة {dept_data['name_ar']}",
                'is_active': True
            }
        )


def remove_departments(apps, schema_editor):
    Department = apps.get_model('core', 'Department')
    Department.objects.filter(code__in=['HR', 'FIN', 'IT', 'OPS', 'LEGAL', 'RISK', 'COMP']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_create_roles'),
    ]

    operations = [
        migrations.RunPython(create_departments, remove_departments),
    ]
