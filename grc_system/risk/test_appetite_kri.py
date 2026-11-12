from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from core import automation
from core.test_utils import GRCTestMixin
from notifications.models import Notification, Escalation
from risk.models import Risk, RiskCategory, RiskAppetite, KeyRiskIndicator, KRIMeasurement
from workflow.models import Task


@override_settings(ALLOWED_HOSTS=['testserver'])
class RiskAppetiteTests(GRCTestMixin, TestCase):
    def setUp(self):
        self.cyber = RiskCategory.objects.create(name='Cyber', code='CYB')
        self.ops = RiskCategory.objects.create(name='Ops', code='OPS')
        RiskAppetite.objects.create(organization=self.org, category=None, statement='Org default',
                                    max_acceptable_score=12, tolerance_score=16)
        RiskAppetite.objects.create(organization=self.org, category=self.cyber, statement='Low appetite for cyber',
                                    max_acceptable_score=6, tolerance_score=12)

    def risk(self, rid, cat, l, i, status='monitoring', **kw):
        return Risk.objects.create(organization=self.org, risk_id=rid, title=rid, category=cat, status=status,
                                   owner=self.it_author, department=self.it_dept, created_by=self.it_author,
                                   inherent_likelihood=l, inherent_impact=i, residual_auto=False, **kw)

    def test_category_statement_overrides_org_default(self):
        r = self.risk('R1', self.cyber, 3, 3)          # 9: within org default, outside cyber appetite
        a = r.appetite_status
        self.assertEqual((a['status'], a['appetite'], a['tolerance'], a['source']), ('tolerance', 6, 12, 'category'))
        r2 = self.risk('R2', self.ops, 3, 3)
        self.assertEqual(r2.appetite_status['status'], 'within')
        self.assertEqual(r2.appetite_status['source'], 'organization')

    def test_residual_used_when_available(self):
        r = self.risk('R3', self.cyber, 5, 5, residual_likelihood=1, residual_impact=3)
        self.assertEqual(r.appetite_status['basis'], 'residual')
        self.assertEqual(r.appetite_status['status'], 'within')

    def test_breach_job_creates_task_and_escalation(self):
        r = self.risk('R4', self.cyber, 4, 4)          # 16 > tolerance 12 -> breach
        result = automation.check_risk_appetite_breaches()
        self.assertEqual(result['breach'], 1)
        self.assertEqual(result['tasks_created'], 1)
        self.assertEqual(result['escalations'], 1)
        task = Task.objects.get(content_type='risk.risk', object_id=r.pk)
        self.assertEqual((task.assigned_to, task.priority, task.task_type), (self.it_author, 'critical', 'remediation'))
        esc = Escalation.objects.get(content_type='risk.risk', object_id=r.pk)
        self.assertEqual(esc.escalated_to, self.it_manager)
        self.assertTrue(Notification.objects.filter(recipient=self.it_manager, subject__startswith='ABOVE TOLERANCE').exists())
        # idempotent
        again = automation.check_risk_appetite_breaches()
        self.assertEqual((again['tasks_created'], again['escalations']), (0, 0))

    def test_exposure_endpoint_and_permissions(self):
        self.risk('R5', self.cyber, 4, 4)
        resp = self.client_for(self.it_author).get('/api/risk/appetites/exposure/', {'organization': self.org.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['counts']['breach'], 1)
        self.assertEqual(resp.data['outside_appetite'][0]['risk_id'], 'R5')
        # authors cannot define appetite
        resp = self.client_for(self.it_author).post('/api/risk/appetites/', {
            'organization': self.org.pk, 'category': self.ops.pk, 'statement': 'x', 'max_acceptable_score': 9, 'tolerance_score': 12})
        self.assertEqual(resp.status_code, 403)
        resp = self.client_for(self.it_manager).post('/api/risk/appetites/', {
            'organization': self.org.pk, 'category': self.ops.pk, 'statement': 'x', 'max_acceptable_score': 9, 'tolerance_score': 6})
        self.assertEqual(resp.status_code, 400)  # tolerance below appetite rejected


@override_settings(ALLOWED_HOSTS=['testserver'])
class KRITests(GRCTestMixin, TestCase):
    def setUp(self):
        self.risk = Risk.objects.create(organization=self.org, risk_id='R1', title='Phishing', owner=self.it_manager,
                                        created_by=self.it_manager, status='monitoring', residual_auto=False)
        self.kri = KeyRiskIndicator.objects.create(
            organization=self.org, risk=self.risk, kri_id='KRI-1', name='Phishing click rate', unit='%',
            direction='up_bad', warning_threshold=Decimal('10'), critical_threshold=Decimal('20'),
            frequency='monthly', owner=self.it_author)

    def test_status_from_thresholds_and_direction(self):
        self.assertEqual(self.kri.status_for(Decimal('5')), 'green')
        self.assertEqual(self.kri.status_for(Decimal('10')), 'amber')
        self.assertEqual(self.kri.status_for(Decimal('25')), 'red')
        down = KeyRiskIndicator(direction='down_bad', warning_threshold=Decimal('95'), critical_threshold=Decimal('90'))
        self.assertEqual(down.status_for(Decimal('99')), 'green')
        self.assertEqual(down.status_for(Decimal('92')), 'amber')
        self.assertEqual(down.status_for(Decimal('80')), 'red')

    def test_measurement_updates_kri_and_alerts_on_red(self):
        client = self.client_for(self.it_author)
        resp = client.post(f'/api/risk/kris/{self.kri.pk}/measure/', {'value': '8'})
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['current_status'], 'green')
        resp = client.post(f'/api/risk/kris/{self.kri.pk}/measure/',
                           {'value': '31', 'measured_at': str(timezone.localdate() + timedelta(days=1))})
        self.assertEqual(resp.data['current_status'], 'red')
        self.assertEqual(KRIMeasurement.objects.filter(kri=self.kri).count(), 2)
        # owner and the linked risk's owner are alerted
        self.assertTrue(Notification.objects.filter(recipient=self.it_author, subject__startswith='KRI RED').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.it_manager, subject__startswith='KRI RED').exists())

    def test_overdue_measurement_reminder(self):
        self.assertTrue(self.kri.is_measurement_overdue)   # never measured
        result = automation.check_kri_status()
        self.assertEqual(result['measurement_overdue'], 1)
        self.assertTrue(Notification.objects.filter(recipient=self.it_author, subject__startswith='KRI measurement overdue').exists())
        KRIMeasurement.objects.create(kri=self.kri, value=Decimal('3'), measured_at=timezone.localdate())
        self.kri.refresh_from_db()
        self.assertFalse(self.kri.is_measurement_overdue)

    def test_kri_dashboard(self):
        KRIMeasurement.objects.create(kri=self.kri, value=Decimal('50'), measured_at=timezone.localdate())
        resp = self.client_for(self.admin).get('/api/risk/kris/dashboard/', {'organization': self.org.pk})
        self.assertEqual(resp.data['counts']['red'], 1)
        self.assertEqual(resp.data['attention'][0]['kri_id'], 'KRI-1')
