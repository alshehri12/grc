"""
Management command to set up department managers.
Ensures that users with 'manager' role are assigned as managers of their departments.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Department, UserProfile, Role


class Command(BaseCommand):
    help = 'Sets up department managers based on user roles'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get all users with manager role
        try:
            manager_role = Role.objects.get(code='manager')
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('Manager role not found'))
            return
        
        # Get all profiles with manager role
        manager_profiles = UserProfile.objects.filter(roles=manager_role)
        
        updated_count = 0
        for profile in manager_profiles:
            if profile.department:
                # Check if department already has a manager
                if profile.department.manager is None:
                    profile.department.manager = profile.user
                    profile.department.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Set {profile.user.username} as manager of {profile.department.name}'
                        )
                    )
                    updated_count += 1
                elif profile.department.manager == profile.user:
                    self.stdout.write(
                        f'{profile.user.username} is already manager of {profile.department.name}'
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'{profile.department.name} already has manager: {profile.department.manager.username}'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'{profile.user.username} has manager role but no department assigned'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated_count} departments'))
        
        # Print summary
        self.stdout.write('\n--- Department Summary ---')
        for dept in Department.objects.all():
            manager_name = dept.manager.username if dept.manager else 'No Manager'
            self.stdout.write(f'  {dept.name}: {manager_name}')
