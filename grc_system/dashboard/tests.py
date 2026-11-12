from django.test import TestCase, override_settings

from core.models import AuditLog
from core.test_utils import GRCTestMixin
from dashboard.models import GeneratedReport
from risk.models import Risk


@override_settings(ALLOWED_HOSTS=['testserver'])
class BoardReportTests(GRCTestMixin, TestCase):
    def setUp(self):
        Risk.objects.create(organization=self.org, risk_id='R1', title='Ransomware', owner=self.it_manager,
                            created_by=self.it_manager, status='monitoring', inherent_likelihood=4, inherent_impact=5, residual_auto=False)

    def test_board_pack_pdf_for_every_type_and_archived(self):
        client = self.client_for(self.it_manager)
        for report_type in ('executive', 'risk', 'compliance', 'bcm'):
            resp = client.get('/api/dashboard/reports/board-pack/', {'organization': self.org.pk, 'type': report_type})
            self.assertEqual(resp.status_code, 200, report_type)
            self.assertEqual(resp['Content-Type'], 'application/pdf')
            self.assertTrue(resp.content.startswith(b'%PDF'), report_type)
        self.assertEqual(GeneratedReport.objects.filter(organization=self.org, status='completed').count(), 4)
        self.assertTrue(AuditLog.objects.filter(action='export', user=self.it_manager).exists())

    def test_invalid_type_rejected(self):
        resp = self.client_for(self.admin).get('/api/dashboard/reports/board-pack/', {'organization': self.org.pk, 'type': 'nope'})
        self.assertEqual(resp.status_code, 400)
