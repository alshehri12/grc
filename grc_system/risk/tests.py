from django.test import TestCase, override_settings

from core.models import Setting
from core.test_utils import GRCTestMixin
from risk.models import Risk
from risk.utils import get_risk_level, get_risk_thresholds, clear_threshold_cache, THRESHOLD_SETTING_KEY


@override_settings(ALLOWED_HOSTS=['testserver'])
class RiskMatrixConsistencyTests(GRCTestMixin, TestCase):
    def setUp(self):
        clear_threshold_cache()
        scores = [(5, 5), (4, 4), (4, 3), (3, 2), (1, 1), (2, 5), (5, 4), (3, 3)]
        for i, (l, im) in enumerate(scores):
            Risk.objects.create(organization=self.org, risk_id=f'R-{i}', title=f'Risk {i}',
                                owner=self.ceo, created_by=self.ceo, inherent_likelihood=l, inherent_impact=im)
        # Approve nothing: risks are pending_approval, which still counts in statistics.

    def test_default_thresholds(self):
        self.assertEqual(get_risk_thresholds(self.org), {'medium': 6, 'high': 12, 'critical': 20})
        self.assertEqual(get_risk_level(25), 'critical')
        self.assertEqual(get_risk_level(20), 'critical')
        self.assertEqual(get_risk_level(19), 'high')
        self.assertEqual(get_risk_level(12), 'high')
        self.assertEqual(get_risk_level(6), 'medium')
        self.assertEqual(get_risk_level(5), 'low')
        self.assertIsNone(get_risk_level(None))

    def test_org_override_changes_levels_everywhere(self):
        Setting.objects.create(organization=self.org, key=THRESHOLD_SETTING_KEY,
                               value='{"medium": 5, "high": 10, "critical": 16}', value_type='json')
        risk = Risk.objects.get(risk_id='R-1')  # 4x4 = 16
        self.assertEqual(risk.risk_level, 'critical')
        resp = self.client_for(self.admin).get('/api/risk/risks/statistics/', {'organization': self.org.pk})
        self.assertEqual(resp.data['thresholds']['critical'], 16)

    def test_statistics_dashboard_and_model_agree(self):
        client = self.client_for(self.admin)
        stats = client.get('/api/risk/risks/statistics/', {'organization': self.org.pk}).data['by_level']
        dash = client.get('/api/dashboard/dashboards/executive_summary/', {'organization': self.org.pk}).data['risks']['by_level']
        expected = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for r in Risk.objects.filter(organization=self.org):
            expected[r.risk_level] += 1
        self.assertEqual(stats, expected)
        self.assertEqual(dash, expected)
        # scores: 25,16,12,6,1,10,20,9 -> critical 2 (25,20), high 2 (16,12), medium 3 (6,10,9), low 1
        self.assertEqual(expected, {'critical': 2, 'high': 2, 'medium': 3, 'low': 1})

    def test_matrix_endpoint_exposes_thresholds(self):
        resp = self.client_for(self.admin).get('/api/risk/risks/matrix/', {'organization': self.org.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('thresholds', resp.data)
        self.assertEqual(resp.data['cells'][4][4]['level'], 'critical')
        self.assertEqual(resp.data['cells'][0][0]['level'], 'low')
