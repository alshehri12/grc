from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

from compliance.models import ControlFramework, ControlDomain, Control, ControlImplementation, Evidence
from core import automation
from core.test_utils import GRCTestMixin
from dashboard.models import KPI, KPIValue
from governance.models import Policy
from notifications.models import Notification
from risk.models import Risk, RiskAcceptance
from risk.utils import calculate_residual_risk, control_effectiveness
from workflow.models import Task


def _impl(org, control, status='implemented', rating=None, maturity=0, owner=None):
    return ControlImplementation.objects.create(organization=org, control=control, status=status,
                                                effectiveness_rating=rating, maturity_level=maturity, owner=owner)


@override_settings(ALLOWED_HOSTS=['testserver'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AutomationJobTests(GRCTestMixin, TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        fw = ControlFramework.objects.create(name='FW', code='FW', version='1')
        dom = ControlDomain.objects.create(framework=fw, code='D', name='Domain')
        self.prev = Control.objects.create(domain=dom, control_id='P-1', title='Preventive', control_type='preventive')
        self.corr = Control.objects.create(domain=dom, control_id='C-1', title='Corrective', control_type='corrective')

    # -- review reminders & dedupe ------------------------------------------------
    def test_policy_review_reminder_is_sent_once(self):
        Policy.objects.create(organization=self.org, policy_id='P1', title='Overdue policy', status='published',
                              owner=self.it_author, created_by=self.it_author, department=self.it_dept,
                              review_date=self.today - timedelta(days=3))
        automation.send_review_reminders()
        automation.send_review_reminders()  # second run must not duplicate
        notes = Notification.objects.filter(content_type='governance.policy', recipient=self.it_author)
        self.assertEqual(notes.count(), 1)
        self.assertTrue(notes.first().subject.startswith('OVERDUE'))
        # department manager is informed too
        self.assertTrue(Notification.objects.filter(content_type='governance.policy', recipient=self.it_manager).exists())

    # -- expiries -----------------------------------------------------------------
    def test_evidence_and_acceptance_expiry(self):
        impl = _impl(self.org, self.prev, owner=self.it_manager)
        old = Evidence.objects.create(organization=self.org, control_implementation=impl, evidence_id='E1', title='Old',
                                      status='accepted', file=ContentFile(b'x', name='e.pdf'),
                                      collection_date=self.today - timedelta(days=400), valid_from=self.today - timedelta(days=400),
                                      valid_until=self.today - timedelta(days=1), submitted_by=self.it_author)
        soon = Evidence.objects.create(organization=self.org, control_implementation=impl, evidence_id='E2', title='Soon',
                                       status='accepted', file=ContentFile(b'x', name='e.pdf'),
                                       collection_date=self.today, valid_from=self.today,
                                       valid_until=self.today + timedelta(days=10), submitted_by=self.it_author)
        risk = Risk.objects.create(organization=self.org, risk_id='R1', title='r', owner=self.ceo, created_by=self.ceo,
                                   status='monitoring')
        acc = RiskAcceptance.objects.create(risk=risk, justification='x', accepted_likelihood=2, accepted_impact=2,
                                            status='approved', valid_from=self.today - timedelta(days=100),
                                            valid_until=self.today - timedelta(days=1), requested_by=self.it_author)

        self.assertEqual(automation.expire_evidence(), {'expired': 1, 'warned': 2})
        self.assertEqual(automation.expire_risk_acceptances()['expired'], 1)
        old.refresh_from_db(); soon.refresh_from_db(); acc.refresh_from_db()
        self.assertEqual(old.status, 'expired')
        self.assertEqual(soon.status, 'accepted')
        self.assertEqual(acc.status, 'expired')
        self.assertTrue(Notification.objects.filter(content_type='compliance.evidence', object_id=old.pk).exists())

    # -- overdue items ------------------------------------------------------------
    def test_overdue_tasks_are_flagged_and_owner_notified(self):
        task = Task.objects.create(title='Late', assigned_to=self.it_author, assigned_by=self.it_manager,
                                   due_date=timezone.now() - timedelta(hours=2), status='pending')
        self.assertEqual(automation.mark_overdue_items()['tasks'], 1)
        task.refresh_from_db()
        self.assertEqual(task.status, 'overdue')
        self.assertEqual(Notification.objects.filter(recipient=self.it_author, content_type='workflow.task').count(), 1)

    # -- email delivery -----------------------------------------------------------
    def test_pending_notifications_are_emailed_and_marked(self):
        n = Notification.objects.create(recipient=self.it_author, subject='Hello', body='Body')
        self.it_manager.email = ''
        self.it_manager.save()
        m = Notification.objects.create(recipient=self.it_manager, subject='No email', body='Body')
        result = automation.deliver_notifications()
        self.assertEqual(result, {'emailed': 1, 'in_app_only': 1, 'failed': 0})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('[GRC] Hello', mail.outbox[0].subject)
        n.refresh_from_db(); m.refresh_from_db()
        self.assertEqual((n.status, m.status), ('sent', 'sent'))
        self.assertIsNotNone(n.sent_at)

    def test_opt_out_respected(self):
        self.it_author.profile.email_notifications = False
        self.it_author.profile.save()
        Notification.objects.create(recipient=self.it_author, subject='x', body='y')
        self.assertEqual(automation.deliver_notifications()['emailed'], 0)
        self.assertEqual(len(mail.outbox), 0)

    # -- KPIs ---------------------------------------------------------------------
    def test_kpi_snapshot(self):
        _impl(self.org, self.prev, 'implemented')
        _impl(self.org, self.corr, 'not_implemented')
        kpi = KPI.objects.create(name='Compliance', code='COMP', calculation_config={'metric': 'compliance_score'})
        automation.snapshot_kpis()
        automation.snapshot_kpis()  # upsert, not duplicate
        values = KPIValue.objects.filter(kpi=kpi, organization=self.org)
        self.assertEqual(values.count(), 1)
        self.assertEqual(values.first().value, Decimal('50.00'))

    # -- registry -----------------------------------------------------------------
    def test_run_all_reports_every_job(self):
        results = automation.run_all()
        self.assertEqual([r['job'] for r in results], list(automation.JOBS))
        self.assertTrue(all(r['ok'] for r in results), results)


@override_settings(ALLOWED_HOSTS=['testserver'])
class ResidualRiskTests(GRCTestMixin, TestCase):
    def setUp(self):
        fw = ControlFramework.objects.create(name='FW', code='FW', version='1')
        dom = ControlDomain.objects.create(framework=fw, code='D', name='Domain')
        self.prev = Control.objects.create(domain=dom, control_id='P-1', title='Preventive', control_type='preventive')
        self.corr = Control.objects.create(domain=dom, control_id='C-1', title='Corrective', control_type='corrective')
        self.missing = Control.objects.create(domain=dom, control_id='M-1', title='Missing', control_type='preventive')
        self.risk = Risk.objects.create(organization=self.org, risk_id='R1', title='r', owner=self.ceo, created_by=self.ceo,
                                        inherent_likelihood=5, inherent_impact=5)

    def test_effectiveness_depends_on_status_and_rating(self):
        self.assertEqual(control_effectiveness(None), 0.0)
        self.assertEqual(control_effectiveness(_impl(self.org, self.prev, 'implemented', rating=5)), 1.0)
        self.assertEqual(control_effectiveness(_impl(self.org, self.corr, 'partially_implemented', rating=4)), 0.4)
        self.assertEqual(control_effectiveness(_impl(self.org, self.missing, 'not_implemented', rating=5)), 0.0)

    def test_rounding_and_caps(self):
        self.assertEqual(calculate_residual_risk(5, 5, 0.8, 0.8), (1, 1, 1))
        self.assertEqual(calculate_residual_risk(5, 5, 0.0, 0.0), (5, 5, 25))
        self.assertEqual(calculate_residual_risk(4, 3, 0.5, 0.0), (2, 3, 6))

    def test_one_strong_control_does_not_mask_missing_ones(self):
        _impl(self.org, self.prev, 'implemented', rating=5)       # strong preventive
        # 'missing' has no implementation at all; 'corr' not implemented
        _impl(self.org, self.corr, 'not_implemented')
        self.risk.controls.add(self.prev, self.corr, self.missing)  # m2m signal recalculates
        self.risk.refresh_from_db()
        # likelihood reduced by the single preventive control (capped at 80%): 5 -> 1
        # impact untouched (no effective corrective control): 5
        self.assertEqual((self.risk.residual_likelihood, self.risk.residual_impact), (1, 5))
        self.assertEqual(self.risk.residual_risk_level, 'low')

    def test_control_status_change_triggers_recalculation(self):
        impl = _impl(self.org, self.corr, 'not_implemented', rating=5)
        self.risk.controls.add(self.corr)
        self.risk.refresh_from_db()
        self.assertEqual(self.risk.residual_impact, 5)
        impl.status = 'implemented'
        impl.save()                                              # post_save signal
        self.risk.refresh_from_db()
        self.assertEqual(self.risk.residual_impact, 2)           # impact reduction is capped at 60%: 5 -> 2
        self.assertEqual(self.risk.residual_likelihood, 5)       # corrective controls do not reduce likelihood

    def test_manual_residual_switches_off_auto_mode(self):
        _impl(self.org, self.prev, 'implemented', rating=5)
        self.risk.controls.add(self.prev)
        client = self.client_for(self.admin)
        resp = client.patch(f'/api/risk/risks/{self.risk.pk}/', {'residual_likelihood': 4, 'residual_impact': 4})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.risk.refresh_from_db()
        self.assertFalse(self.risk.residual_auto)
        automation.recalculate_residual_risks()
        self.risk.refresh_from_db()
        self.assertEqual((self.risk.residual_likelihood, self.risk.residual_impact), (4, 4))
        resp = client.post(f'/api/risk/risks/{self.risk.pk}/calculate_residual/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residual_likelihood'], 1)
        self.risk.refresh_from_db()
        self.assertTrue(self.risk.residual_auto)
