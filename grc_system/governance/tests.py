from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from core.test_utils import GRCTestMixin
from governance.models import Policy, Document


@override_settings(ALLOWED_HOSTS=['testserver'])
class GovernanceVisibilityTests(GRCTestMixin, TestCase):
    def setUp(self):
        def policy(pid, status, creator):
            return Policy.objects.create(organization=self.org, policy_id=pid, title=pid, status=status,
                                         owner=creator, created_by=creator, department=self.exec_dept)
        # statuses are set explicitly, so bypass the auto-submit by creating as approved/published/draft
        self.published = policy('PUB', 'published', self.ceo)
        self.approved = policy('APP', 'approved', self.ceo)
        self.ceo_draft = policy('DRAFT', 'draft', self.ceo)
        self.retired = policy('RET', 'retired', self.ceo)
        self.doc = Document.objects.create(
            organization=self.org, document_id='DOC-1', title='Guideline', document_type='guideline',
            status='active', file=ContentFile(b'x', name='g.pdf'), owner=self.ceo, created_by=self.ceo)

    def ids(self, user, path):
        data = self.client_for(user).get(path).data
        return {row['policy_id'] if 'policy_id' in row else row['document_id'] for row in data['results']}

    def test_published_and_approved_policies_visible_to_everyone(self):
        self.assertEqual(self.ids(self.it_author, '/api/governance/policies/'), {'PUB', 'APP'})

    def test_drafts_of_others_hidden_but_admin_sees_all(self):
        self.assertEqual(self.ids(self.admin, '/api/governance/policies/'), {'PUB', 'APP', 'DRAFT', 'RET'})
        self.assertIn('DRAFT', self.ids(self.ceo, '/api/governance/policies/'))

    def test_active_documents_visible_to_everyone(self):
        self.assertEqual(self.ids(self.it_author, '/api/governance/documents/'), {'DOC-1'})

    def test_author_cannot_approve_or_publish(self):
        client = self.client_for(self.it_author)
        self.assertEqual(client.post(f'/api/governance/policies/{self.approved.pk}/publish/').status_code, 403)

    def test_manager_cannot_approve_own_policy(self):
        pending = Policy.objects.create(organization=self.org, policy_id='MINE', title='Mine', status='pending_review',
                                        owner=self.ceo, created_by=self.ceo, department=self.it_dept)
        self.assertEqual(self.client_for(self.ceo).post(f'/api/governance/policies/{pending.pk}/approve/').status_code, 403)
        # a manager of another department cannot even see it
        self.assertEqual(self.client_for(self.other_author).post(f'/api/governance/policies/{pending.pk}/approve/').status_code, 404)
        resp = self.client_for(self.it_manager).post(f'/api/governance/policies/{pending.pk}/approve/')
        self.assertEqual(resp.status_code, 200, resp.data)
        pending.refresh_from_db()
        self.assertEqual(pending.status, 'approved')

    def test_publish_requires_manager_and_approved_state(self):
        resp = self.client_for(self.ceo).post(f'/api/governance/policies/{self.approved.pk}/publish/')
        self.assertEqual(resp.status_code, 200)
        self.approved.refresh_from_db()
        self.assertEqual(self.approved.status, 'published')
        self.assertIsNotNone(self.approved.effective_date)
