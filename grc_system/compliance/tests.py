from django.test import TestCase, override_settings

from compliance.models import ControlFramework, ControlDomain, Control, ControlImplementation, GapAssessment
from core.test_utils import GRCTestMixin


@override_settings(ALLOWED_HOSTS=['testserver'])
class StatementOfApplicabilityTests(GRCTestMixin, TestCase):
    def setUp(self):
        self.fw = ControlFramework.objects.create(name='ISO', code='ISO', version='2022')
        dom = ControlDomain.objects.create(framework=self.fw, code='A.5', name='Org')
        self.c1 = Control.objects.create(domain=dom, control_id='A.5.1', title='Policies')
        self.c2 = Control.objects.create(domain=dom, control_id='A.5.23', title='Cloud')
        self.c3 = Control.objects.create(domain=dom, control_id='A.5.30', title='ICT readiness')
        self.i1 = ControlImplementation.objects.create(organization=self.org, control=self.c1, status='implemented', maturity_level=4)
        self.i2 = ControlImplementation.objects.create(organization=self.org, control=self.c2, status='not_applicable',
                                                       applicability_justification='No cloud services are used.')

    def test_not_applicable_requires_justification(self):
        client = self.client_for(self.admin)
        resp = client.patch(f'/api/compliance/implementations/{self.i1.pk}/', {'status': 'not_applicable'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('applicability_justification', resp.data)
        resp = client.patch(f'/api/compliance/implementations/{self.i1.pk}/',
                            {'status': 'not_applicable', 'applicability_justification': 'Out of scope'})
        self.assertEqual(resp.status_code, 200)

    def test_soa_rows_and_summary(self):
        resp = self.client_for(self.it_author).get('/api/compliance/implementations/statement_of_applicability/',
                                                   {'organization': self.org.pk, 'framework': self.fw.pk})
        self.assertEqual(resp.status_code, 200)
        s = resp.data['summary']
        self.assertEqual((s['total'], s['applicable'], s['not_applicable'], s['no_record'], s['missing_justification']), (3, 2, 1, 1, 0))
        by_id = {r['control_id']: r for r in resp.data['rows']}
        self.assertFalse(by_id['A.5.23']['applicable'])
        self.assertEqual(by_id['A.5.23']['justification'], 'No cloud services are used.')
        self.assertEqual(by_id['A.5.30']['status'], 'no_record')

    def test_soa_pdf(self):
        resp = self.client_for(self.admin).get('/api/compliance/implementations/statement_of_applicability/',
                                               {'organization': self.org.pk, 'framework': self.fw.pk, 'output': 'pdf'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))

    def test_gap_assessment_recalculates_from_implementations(self):
        ga = GapAssessment.objects.create(organization=self.org, framework=self.fw, assessment_id='GAP-1', title='Gap', status='in_progress')
        resp = self.client_for(self.it_manager).post(f'/api/compliance/gap-assessments/{ga.pk}/calculate_score/')
        self.assertEqual(resp.status_code, 200, resp.data)
        ga.refresh_from_db()
        # 3 controls, 1 N/A -> 2 applicable, 1 implemented -> 50%
        self.assertEqual((ga.total_controls, ga.not_applicable, ga.implemented_controls), (3, 1, 1))
        self.assertEqual(float(ga.compliance_score), 50.0)
        ga.status = 'approved'
        ga.save()
        self.assertEqual(self.client_for(self.it_manager).post(f'/api/compliance/gap-assessments/{ga.pk}/calculate_score/').status_code, 400)
