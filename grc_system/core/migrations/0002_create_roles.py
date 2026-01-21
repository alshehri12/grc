# Generated migration to create Author and Manager roles

from django.db import migrations


def create_roles(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    
    # Create Author role
    Role.objects.get_or_create(
        code='author',
        defaults={
            'name': 'Author',
            'name_ar': 'مؤلف',
            'role_type': 'grc',
            'description': 'Can create and edit content. All content requires manager approval before publication.',
            'description_ar': 'يمكنه إنشاء وتعديل المحتوى. يتطلب جميع المحتوى موافقة المدير قبل النشر.',
            'permissions': {
                'governance': {'policy': ['create', 'read', 'update'], 'procedure': ['create', 'read', 'update']},
                'risk': {'risk': ['create', 'read', 'update']},
                'bcm': {'function': ['create', 'read', 'update'], 'plan': ['create', 'read', 'update']},
                'compliance': {'control': ['create', 'read', 'update'], 'audit': ['create', 'read', 'update']}
            },
            'is_active': True
        }
    )
    
    # Create Manager role
    Role.objects.get_or_create(
        code='manager',
        defaults={
            'name': 'Manager',
            'name_ar': 'مدير',
            'role_type': 'grc',
            'description': 'Can approve content created by authors. Full access to department content.',
            'description_ar': 'يمكنه الموافقة على المحتوى الذي أنشأه المؤلفون. وصول كامل لمحتوى الإدارة.',
            'permissions': {
                'governance': {'policy': ['create', 'read', 'update', 'delete', 'approve'], 'procedure': ['create', 'read', 'update', 'delete', 'approve']},
                'risk': {'risk': ['create', 'read', 'update', 'delete', 'approve']},
                'bcm': {'function': ['create', 'read', 'update', 'delete', 'approve'], 'plan': ['create', 'read', 'update', 'delete', 'approve']},
                'compliance': {'control': ['create', 'read', 'update', 'delete', 'approve'], 'audit': ['create', 'read', 'update', 'delete', 'approve']}
            },
            'is_active': True
        }
    )
    
    # Create Admin role
    Role.objects.get_or_create(
        code='admin',
        defaults={
            'name': 'Admin',
            'name_ar': 'مسؤول النظام',
            'role_type': 'system',
            'description': 'Full system access including user management and settings.',
            'description_ar': 'وصول كامل للنظام بما في ذلك إدارة المستخدمين والإعدادات.',
            'permissions': {'all': True},
            'is_active': True
        }
    )


def remove_roles(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    Role.objects.filter(code__in=['author', 'manager', 'admin']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_roles, remove_roles),
    ]
