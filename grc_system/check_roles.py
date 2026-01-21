import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grc_system.settings')

import django
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile, Role

print("=== All Users ===")
for u in User.objects.all():
    try:
        profile = u.profile
        roles = list(profile.roles.values_list("name", flat=True))
        dept = profile.department.name if profile.department else "None"
        print(f"  {u.username}: roles={roles}, department={dept}")
    except UserProfile.DoesNotExist:
        print(f"  {u.username}: No profile")

print("\n=== All Roles ===")
for r in Role.objects.all():
    print(f"  {r.name} ({r.code})")
