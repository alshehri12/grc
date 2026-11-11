"""
Shared fixtures for GRC tests.

Builds a small organization:
  EXEC (manager: ceo)
   └── IT (manager: it_manager)  members: it_manager, it_author
  plus a superuser `admin`.
Roles (admin/manager/author) and the content-approval workflow template
come from the data migrations.
"""
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Organization, Department, Role, UserProfile


class GRCTestMixin:
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name='Test Org', code='TST')
        cls.exec_dept = Department.objects.create(organization=cls.org, name='Executive', code='EXEC')
        cls.it_dept = Department.objects.create(organization=cls.org, name='IT', code='IT', parent=cls.exec_dept)

        roles = {r.code: r for r in Role.objects.all()}
        cls.roles = roles

        def make(username, dept, role=None, superuser=False):
            if superuser:
                user = User.objects.create_superuser(username, f'{username}@test.local', 'pw')
            else:
                user = User.objects.create_user(username, f'{username}@test.local', 'pw')
            profile = UserProfile.objects.create(user=user, organization=cls.org, department=dept)
            if role:
                profile.roles.add(roles[role])
            return user

        cls.admin = make('admin', cls.it_dept, 'admin', superuser=True)
        cls.ceo = make('ceo', cls.exec_dept, 'manager')
        cls.it_manager = make('it_manager', cls.it_dept, 'manager')
        cls.it_author = make('it_author', cls.it_dept, 'author')
        cls.other_author = make('other_author', cls.exec_dept, 'author')

        cls.exec_dept.manager = cls.ceo
        cls.exec_dept.save()
        cls.it_dept.manager = cls.it_manager
        cls.it_dept.save()

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client
