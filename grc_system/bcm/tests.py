from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from bcm.models import (
    BusinessFunction, BusinessImpactAnalysis, BCPlan, DisasterRecoveryPlan, BCMTest, CrisisIncident,
)
from bcm.utils import capability_analysis, plan_test_status
from core import automation
from core.test_utils import GRCTestMixin
from notifications.models import Notification
from risk.models import Asset, Risk
from workflow.models import Task


@override_settings(ALLOWED_HOSTS=['testserver'])
class CapabilityAnalysisTests(GRCTestMixin, TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.db = Asset.objects.create(organization=self.org, asset_id='A-DB', name='Customer DB', owner=self.it_manager)
        self.web = Asset.objects.create(organization=self.org, asset_id='A-WEB', name='Portal', owner=self.it_manager)
        self.fn = BusinessFunction.objects.create(organization=self.org, function_id='BF-1', name='Payments',
                                                  description='x', criticality='critical', status='active',
                                                  owner=self.ceo, created_by=self.ceo)
        self.bia = BusinessImpactAnalysis.objects.create(organization=self.org, business_function=self.fn, status='approved',
                                                         assessment_date=self.today, rto_hours=4, rpo_hours=1, mtpd_hours=24)
        self.bia.dependent_assets.add(self.db, self.web)
        self.plan = DisasterRecoveryPlan.objects.create(organization=self.org, plan_id='DRP-1', title='DB failover',
                                                        status='active', owner=self.it_manager, created_by=self.it_manager,
                                                        achievable_rto_hours=2, achievable_rpo_hours=1)
        self.plan.covered_assets.add(self.db)
        # New content is routed to approval by the maker-checker signals; simulate approved records.
        BusinessFunction.objects.filter(pk=self.fn.pk).update(status='active')
        DisasterRecoveryPlan.objects.filter(pk=self.plan.pk).update(status='active')
        self.fn.refresh_from_db(); self.plan.refresh_from_db()

    def report(self):
        return capability_analysis(self.org)['functions'][0]

    def test_no_bia(self):
        self.bia.delete()
        self.assertEqual(self.report()['status'], 'no_bia')

    def test_missing_dr_plan_for_a_dependency(self):
        row = self.report()
        self.assertEqual(row['status'], 'no_dr_plan')
        self.assertIn('Portal: no approved DR plan covers this system', row['issues'])

    def test_gap_when_achievable_worse_than_required(self):
        self.plan.covered_assets.add(self.web)
        self.plan.achievable_rto_hours = 8
        self.plan.save()
        row = self.report()
        self.assertEqual(row['status'], 'gap')
        self.assertEqual(row['achievable']['rto_hours'], 8)

    def test_untested_then_unproven_then_covered(self):
        self.plan.covered_assets.add(self.web)
        self.assertEqual(self.report()['status'], 'untested')

        test = BCMTest.objects.create(organization=self.org, test_id='T-1', title='Failover', test_type='simulation',
                                      status='completed', dr_plan=self.plan, scenario='x', scheduled_date=self.today,
                                      actual_end=timezone.now(), achieved_rto_hours=Decimal('6'), coordinator=self.it_manager,
                                      created_by=self.it_manager)
        self.assertEqual(self.report()['status'], 'unproven')

        test.achieved_rto_hours = Decimal('3')
        test.save()
        row = self.report()
        self.assertEqual(row['status'], 'covered')
        self.assertEqual(row['proven']['rto_hours'], 3.0)

        # a stale exercise no longer counts as proof
        test.actual_end = timezone.now() - timedelta(days=400)
        test.save()
        self.assertEqual(self.report()['status'], 'untested')

    def test_endpoint_and_gap_job(self):
        resp = self.client_for(self.it_author).get('/api/bcm/functions/capability_analysis/', {'organization': self.org.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['summary']['no_dr_plan'], 1)
        self.assertEqual(resp.data['summary']['critical_at_risk'], 1)
        result = automation.check_capability_gaps()
        self.assertEqual(result['gaps'], 1)
        self.assertTrue(Notification.objects.filter(recipient=self.ceo, subject__startswith='Recovery capability gap').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.it_manager, subject__startswith='Recovery capability gap').exists())

    def test_dashboard_includes_capability(self):
        resp = self.client_for(self.admin).get('/api/dashboard/dashboards/executive_summary/', {'organization': self.org.pk})
        self.assertEqual(resp.data['bcm']['capability']['total'], 1)
        self.assertEqual(resp.data['risks']['appetite']['within'], 0)


@override_settings(ALLOWED_HOSTS=['testserver'])
class ExerciseScheduleTests(GRCTestMixin, TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.plan = BCPlan.objects.create(organization=self.org, plan_id='BCP-1', title='Corporate', status='active',
                                          owner=self.ceo, created_by=self.ceo, test_frequency_months=6)
        self.dr = DisasterRecoveryPlan.objects.create(organization=self.org, plan_id='DRP-1', title='DR', status='active',
                                                      owner=self.it_manager, created_by=self.it_manager)

    def test_never_tested_plan_is_overdue(self):
        ts = plan_test_status(self.plan)
        self.assertTrue(ts['overdue'])

    def test_completing_a_test_schedules_the_next_one(self):
        test = BCMTest.objects.create(organization=self.org, test_id='T-1', title='Tabletop', status='in_progress',
                                      bc_plan=self.plan, dr_plan=self.dr, scenario='x', scheduled_date=self.today,
                                      coordinator=self.it_manager, created_by=self.it_manager)
        resp = self.client_for(self.it_manager).post(f'/api/bcm/tests/{test.pk}/complete/',
                                                     {'result': 'pass', 'achieved_rto_hours': '3.5'})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.plan.refresh_from_db(); self.dr.refresh_from_db(); test.refresh_from_db()
        self.assertEqual(self.plan.last_tested_date, self.today)
        self.assertEqual(self.plan.next_test_date, self.today + timedelta(days=180))
        self.assertEqual(self.dr.next_test_date, self.today + timedelta(days=360))
        self.assertEqual(test.achieved_rto_hours, Decimal('3.5'))
        self.assertFalse(plan_test_status(self.plan)['needs_testing'])

    def test_reminder_uses_plan_frequency(self):
        self.plan.last_tested_date = self.today - timedelta(days=200)
        self.plan.next_test_date = self.today - timedelta(days=20)
        self.plan.save()
        automation.send_review_reminders()
        self.assertTrue(Notification.objects.filter(recipient=self.ceo, subject__startswith='OVERDUE exercise').exists())


@override_settings(ALLOWED_HOSTS=['testserver'])
class IncidentRiskLinkTests(GRCTestMixin, TestCase):
    def test_linking_incident_creates_reassessment_task_once(self):
        risk = Risk.objects.create(organization=self.org, risk_id='R1', title='Ransomware', owner=self.it_manager,
                                   created_by=self.it_manager, status='monitoring', residual_auto=False)
        incident = CrisisIncident.objects.create(organization=self.org, incident_id='INC-1', title='Ransomware outbreak',
                                                 incident_type='cyber_attack', severity='critical', description='x',
                                                 impact_description='x', reported_at=timezone.now(), reported_by=self.it_author)
        incident.related_risks.add(risk)
        incident.related_risks.remove(risk)
        incident.related_risks.add(risk)
        tasks = Task.objects.filter(content_type='risk.risk', object_id=risk.pk, task_type='assessment')
        self.assertEqual(tasks.count(), 1)
        self.assertEqual((tasks[0].assigned_to, tasks[0].priority), (self.it_manager, 'high'))
        self.assertTrue(Notification.objects.filter(recipient=self.it_manager, subject__startswith='Risk materialised').exists())

    def test_threat_profile_endpoint(self):
        asset = Asset.objects.create(organization=self.org, asset_id='A-1', name='ERP', owner=self.it_manager)
        fn = BusinessFunction.objects.create(organization=self.org, function_id='BF-1', name='Payroll', description='x',
                                             criticality='essential', status='active', owner=self.ceo, created_by=self.ceo)
        fn.related_assets.add(asset)
        r1 = Risk.objects.create(organization=self.org, risk_id='R1', title='ERP outage', owner=self.it_manager,
                                 created_by=self.it_manager, status='monitoring', inherent_likelihood=3, inherent_impact=4, residual_auto=False)
        r1.assets.add(asset)
        r2 = Risk.objects.create(organization=self.org, risk_id='R2', title='Key person', owner=self.it_manager,
                                 created_by=self.it_manager, status='monitoring', residual_auto=False)
        fn.related_risks.add(r2)
        resp = self.client_for(self.it_author).get(f'/api/bcm/functions/{fn.pk}/threat_profile/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['summary']['total'], 2)
        self.assertEqual({r['risk_id'] for r in resp.data['risks']}, {'R1', 'R2'})
