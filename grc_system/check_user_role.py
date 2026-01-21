"""
Script to check user roles.
Run with: python manage.py shell < check_user_role.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grc_system.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile, Role

# Find user ahmed
users = User.objects.filter(username__icontains='ahmed')

if not users.exists():
    print("No user found with 'ahmed' in username")
    print("\nAll users in system:")
    for u in User.objects.all():
        print(f"  - {u.username} ({u.first_name} {u.last_name})")
else:
    for user in users:
        print(f"\n=== User: {user.username} ===")
        print(f"Name: {user.first_name} {user.last_name}")
        print(f"Email: {user.email}")
        print(f"Is Superuser: {user.is_superuser}")
        
        try:
            profile = user.profile
            print(f"Department: {profile.department.name if profile.department else 'None'}")
            roles = profile.roles.all()
            if roles:
                print(f"Roles: {', '.join([r.name for r in roles])}")
            else:
                print("Roles: None assigned")
        except UserProfile.DoesNotExist:
            print("No profile exists for this user")

print("\n=== Available Roles ===")
for role in Role.objects.all():
    print(f"  - {role.name} ({role.code})")
