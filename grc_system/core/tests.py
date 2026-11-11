from django.test import TestCase, override_settings

from core.models import AuditLog, Role
from core.test_utils import GRCTestMixin


@override_settings(ALLOWED_HOSTS=['testserver'])
class PermissionTests(GRCTestMixin, TestCase):
    def test_non_admin_cannot_modify_reference_data(self):
        payload = {'name': 'Hacker', 'code': 'hack'}
        for user in (self.it_author, self.it_manager):
            resp = self.client_for(user).post('/api/core/roles/', payload)
            self.assertEqual(resp.status_code, 403, user.username)
            resp = self.client_for(user).patch(f'/api/core/users/{self.admin.pk}/', {'is_active': False})
            self.assertEqual(resp.status_code, 403, user.username)
        self.assertFalse(Role.objects.filter(code='hack').exists())

    def test_admin_can_modify_reference_data(self):
        resp = self.client_for(self.admin).post('/api/core/roles/', {'name': 'Auditor', 'code': 'auditor'})
        self.assertEqual(resp.status_code, 201)

    def test_everyone_can_read_reference_data(self):
        resp = self.client_for(self.it_author).get('/api/core/departments/')
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_grant_self_roles_via_me(self):
        admin_role = self.roles['admin'].pk
        resp = self.client_for(self.it_author).patch('/api/core/profiles/me/', {'roles': [admin_role], 'phone': '123'})
        self.assertEqual(resp.status_code, 200)
        self.it_author.profile.refresh_from_db()
        self.assertFalse(self.it_author.profile.roles.filter(code='admin').exists())
        self.assertEqual(self.it_author.profile.phone, '123')

    def test_audit_log_only_for_managers_and_admins(self):
        self.assertEqual(self.client_for(self.it_author).get('/api/core/audit-logs/').status_code, 403)
        self.assertEqual(self.client_for(self.it_manager).get('/api/core/audit-logs/').status_code, 200)


@override_settings(ALLOWED_HOSTS=['testserver'])
class AuditTrailTests(GRCTestMixin, TestCase):
    def test_create_update_delete_are_logged_with_diff(self):
        client = self.client_for(self.admin)
        resp = client.post('/api/risk/asset-categories/', {'name': 'Servers', 'code': 'SRV'})
        self.assertEqual(resp.status_code, 201, resp.data)
        pk = resp.data['id']

        resp = client.patch(f'/api/risk/asset-categories/{pk}/', {'name': 'Physical Servers'})
        self.assertEqual(resp.status_code, 200)
        resp = client.delete(f'/api/risk/asset-categories/{pk}/')
        self.assertEqual(resp.status_code, 204)

        logs = AuditLog.objects.filter(content_type='risk.assetcategory', object_id=str(pk)).order_by('timestamp')
        self.assertEqual([l.action for l in logs], ['create', 'update', 'delete'])
        self.assertEqual(logs[1].changes['name'], ['Servers', 'Physical Servers'])
        self.assertEqual(logs[0].user, self.admin)
