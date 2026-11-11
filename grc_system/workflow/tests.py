from django.test import TestCase, override_settings

from core.models import AuditLog
from core.test_utils import GRCTestMixin
from governance.models import Policy
from workflow.models import Approval, WorkflowInstance
from workflow.services import WorkflowService


def make_policy(org, dept, creator, **kw):
    defaults = dict(policy_id=f'POL-{creator.username}-{Policy.objects.count() + 1}', title='Test Policy',
                    owner=creator, department=dept, created_by=creator)
    defaults.update(kw)
    return Policy.objects.create(organization=org, **defaults)


@override_settings(ALLOWED_HOSTS=['testserver'])
class MakerCheckerTests(GRCTestMixin, TestCase):
    def test_author_content_goes_to_department_manager(self):
        policy = make_policy(self.org, self.it_dept, self.it_author)
        policy.refresh_from_db()
        self.assertEqual(policy.status, 'pending_approval')
        approval = Approval.objects.get(workflow_instance__object_id=policy.pk)
        self.assertEqual(approval.assignee, self.it_manager)

    def test_manager_content_is_not_auto_approved_and_routes_up(self):
        policy = make_policy(self.org, self.it_dept, self.it_manager)
        policy.refresh_from_db()
        self.assertEqual(policy.status, 'pending_approval')
        approval = Approval.objects.get(workflow_instance__object_id=policy.pk)
        self.assertEqual(approval.assignee, self.ceo)  # parent department manager, never the maker

    def test_only_assignee_can_approve(self):
        policy = make_policy(self.org, self.it_dept, self.it_author)
        approval = Approval.objects.get(workflow_instance__object_id=policy.pk)

        # another author: forbidden
        resp = self.client_for(self.other_author).post(f'/api/workflow/approvals/{approval.pk}/approve/', {})
        self.assertIn(resp.status_code, (403, 404))
        # the maker: forbidden even if they somehow reach it
        resp = self.client_for(self.it_author).post(f'/api/workflow/approvals/{approval.pk}/approve/', {})
        self.assertEqual(resp.status_code, 403)
        # the assigned manager: OK
        resp = self.client_for(self.it_manager).post(f'/api/workflow/approvals/{approval.pk}/approve/', {'comments': 'ok'})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data['workflow_completed'])

        policy.refresh_from_db()
        self.assertEqual(policy.status, 'approved')
        self.assertEqual(policy.approved_by, self.it_manager)
        self.assertTrue(AuditLog.objects.filter(action='approve', content_type='governance.policy',
                                                object_id=str(policy.pk), user=self.it_manager).exists())

    def test_admin_cannot_approve_own_submission(self):
        policy = make_policy(self.org, self.it_dept, self.admin)
        approval = Approval.objects.get(workflow_instance__object_id=policy.pk)
        self.assertNotEqual(approval.assignee, self.admin)
        resp = self.client_for(self.admin).post(f'/api/workflow/approvals/{approval.pk}/approve/', {})
        self.assertEqual(resp.status_code, 403)

    def test_reject_requires_reason_and_returns_to_draft(self):
        policy = make_policy(self.org, self.it_dept, self.it_author)
        approval = Approval.objects.get(workflow_instance__object_id=policy.pk)
        client = self.client_for(self.it_manager)
        self.assertEqual(client.post(f'/api/workflow/approvals/{approval.pk}/reject/', {}).status_code, 400)
        resp = client.post(f'/api/workflow/approvals/{approval.pk}/reject/', {'comments': 'incomplete'})
        self.assertEqual(resp.status_code, 200, resp.data)
        policy.refresh_from_db()
        self.assertEqual(policy.status, 'draft')

    def test_cancel_only_by_initiator_or_admin(self):
        policy = make_policy(self.org, self.it_dept, self.it_author)
        wf = WorkflowInstance.objects.get(object_id=policy.pk, content_type='governance.policy')
        self.assertIn(self.client_for(self.other_author).post(f'/api/workflow/instances/{wf.pk}/cancel/', {}).status_code, (403, 404))
        resp = self.client_for(self.it_author).post(f'/api/workflow/instances/{wf.pk}/cancel/', {'reason': 'oops'})
        self.assertEqual(resp.status_code, 200, resp.data)
        wf.refresh_from_db()
        self.assertEqual(wf.status, 'cancelled')
        self.assertFalse(wf.approvals.filter(status='pending').exists())

    def test_service_rejects_wrong_user(self):
        policy = make_policy(self.org, self.it_dept, self.it_author)
        approval = Approval.objects.get(workflow_instance__object_id=policy.pk)
        with self.assertRaises(PermissionError):
            WorkflowService.handle_approval_decision(approval, 'approved', self.other_author)

    def test_non_admin_sees_only_own_approvals(self):
        make_policy(self.org, self.it_dept, self.it_author)
        resp = self.client_for(self.other_author).get('/api/workflow/approvals/')
        self.assertEqual(resp.data['count'], 0)
        resp = self.client_for(self.it_manager).get('/api/workflow/approvals/my_pending/')
        self.assertEqual(len(resp.data), 1)
