"""
Risk Management Utilities - core GRC logic for risk calculations.

1. Risk Score = Likelihood x Impact (5x5 matrix, 1-25)
2. Risk Level from a SINGLE configurable threshold table (see get_risk_thresholds)
3. Residual Risk = Inherent Risk adjusted by control effectiveness
4. Risk Appetite comparison

The level thresholds are the one source of truth for the model, the API
statistics, the dashboard and the frontend. They can be overridden per
organization through core.Setting key `risk_matrix_thresholds` holding JSON
such as {"medium": 6, "high": 12, "critical": 20} (score >= value).
"""
import json

from django.core.exceptions import ValidationError

THRESHOLD_SETTING_KEY = 'risk_matrix_thresholds'

# Default thresholds (score >= value). low is everything below `medium`.
DEFAULT_THRESHOLDS = {'medium': 6, 'high': 12, 'critical': 20}

LEVEL_META = {
    'low':      {'color': '#4CAF50', 'label': 'Low', 'label_ar': 'منخفض',
                 'action': 'Monitor and review periodically'},
    'medium':   {'color': '#FFC107', 'label': 'Medium', 'label_ar': 'متوسط',
                 'action': 'Implement controls within 6 months'},
    'high':     {'color': '#FF5722', 'label': 'High', 'label_ar': 'عالي',
                 'action': 'Immediate action required within 3 months'},
    'critical': {'color': '#F44336', 'label': 'Critical', 'label_ar': 'حرج',
                 'action': 'Escalate to senior management immediately'},
}
LEVEL_ORDER = ['low', 'medium', 'high', 'critical']

# Likelihood Labels (ISO 31000 aligned)
LIKELIHOOD_LABELS = {
    1: {'en': 'Rare', 'ar': 'نادر', 'description': 'May occur only in exceptional circumstances (< 5%)'},
    2: {'en': 'Unlikely', 'ar': 'غير محتمل', 'description': 'Could occur at some time (5-25%)'},
    3: {'en': 'Possible', 'ar': 'محتمل', 'description': 'Might occur at some time (25-50%)'},
    4: {'en': 'Likely', 'ar': 'مرجح', 'description': 'Will probably occur in most circumstances (50-75%)'},
    5: {'en': 'Almost Certain', 'ar': 'شبه مؤكد', 'description': 'Expected to occur in most circumstances (> 75%)'},
}

# Impact Labels (Multi-dimensional)
IMPACT_LABELS = {
    1: {'en': 'Insignificant', 'ar': 'غير مؤثر', 'financial': '< 10K SAR', 'operational': 'No disruption'},
    2: {'en': 'Minor', 'ar': 'طفيف', 'financial': '10K - 100K SAR', 'operational': '< 4 hours'},
    3: {'en': 'Moderate', 'ar': 'متوسط', 'financial': '100K - 1M SAR', 'operational': '4-24 hours'},
    4: {'en': 'Major', 'ar': 'كبير', 'financial': '1M - 10M SAR', 'operational': '1-7 days'},
    5: {'en': 'Catastrophic', 'ar': 'كارثي', 'financial': '> 10M SAR', 'operational': '> 7 days'},
}

_threshold_cache = {}


def clear_threshold_cache():
    _threshold_cache.clear()


def _org_id(organization):
    if organization is None:
        return None
    return getattr(organization, 'pk', organization)


def get_risk_thresholds(organization=None):
    """
    Return {'medium': n, 'high': n, 'critical': n} for the organization
    (falls back to the system-wide setting, then to DEFAULT_THRESHOLDS).
    """
    org_id = _org_id(organization)
    if org_id in _threshold_cache:
        return _threshold_cache[org_id]

    thresholds = dict(DEFAULT_THRESHOLDS)
    try:
        from core.models import Setting
        candidates = Setting.objects.filter(key=THRESHOLD_SETTING_KEY)
        setting = None
        if org_id is not None:
            setting = candidates.filter(organization_id=org_id).first()
        if setting is None:
            setting = candidates.filter(organization__isnull=True).first()
        if setting:
            data = json.loads(setting.value) if isinstance(setting.value, str) else setting.value
            parsed = {k: int(data[k]) for k in ('medium', 'high', 'critical') if k in data}
            if len(parsed) == 3 and 1 < parsed['medium'] < parsed['high'] < parsed['critical'] <= 25:
                thresholds = parsed
    except Exception:
        pass  # DB not ready or malformed setting: use defaults

    _threshold_cache[org_id] = thresholds
    return thresholds


def get_risk_levels(organization=None):
    """
    Full level table for the organization:
    {'low': {'min': 1, 'max': 5, 'color': ..., 'label': ..., 'action': ...}, ...}
    """
    t = get_risk_thresholds(organization)
    bounds = {
        'low': (1, t['medium'] - 1),
        'medium': (t['medium'], t['high'] - 1),
        'high': (t['high'], t['critical'] - 1),
        'critical': (t['critical'], 25),
    }
    return {level: {'min': lo, 'max': hi, **LEVEL_META[level]} for level, (lo, hi) in bounds.items()}


def validate_risk_score(value, field_name='score'):
    """Validate that risk likelihood/impact is between 1-5."""
    if value is not None and (value < 1 or value > 5):
        raise ValidationError(f'{field_name} must be between 1 and 5')


def calculate_risk_score(likelihood, impact):
    """Risk score = likelihood x impact (1-25), or None when either is missing."""
    if likelihood is None or impact is None:
        return None
    return likelihood * impact


def get_risk_level(score, organization=None):
    """Map a score (1-25) to low/medium/high/critical using the organization's thresholds."""
    if score is None:
        return None
    t = get_risk_thresholds(organization)
    if score >= t['critical']:
        return 'critical'
    if score >= t['high']:
        return 'high'
    if score >= t['medium']:
        return 'medium'
    return 'low'


def get_risk_color(score, organization=None):
    """Color code for a risk score."""
    level = get_risk_level(score, organization)
    return LEVEL_META.get(level, {}).get('color', '#9E9E9E')


def build_matrix_cells(organization=None):
    """5x5 grid of {likelihood, impact, score, level, color} for heat-map rendering."""
    return [
        [
            {'likelihood': l, 'impact': i, 'score': l * i,
             'level': get_risk_level(l * i, organization), 'color': get_risk_color(l * i, organization)}
            for i in range(1, 6)
        ]
        for l in range(1, 6)
    ]


def calculate_residual_risk(inherent_likelihood, inherent_impact, control_effectiveness_pct):
    """
    Calculate residual risk after control application.
    
    Formula: Residual = Inherent × (1 - Control Effectiveness)
    
    Args:
        inherent_likelihood: Inherent likelihood (1-5)
        inherent_impact: Inherent impact (1-5)
        control_effectiveness_pct: Control effectiveness percentage (0-100)
    
    Returns:
        tuple: (residual_likelihood, residual_impact, residual_score)
    """
    if inherent_likelihood is None or inherent_impact is None:
        return None, None, None
    
    # Control effectiveness reduces likelihood (controls prevent occurrence)
    effectiveness_factor = 1 - (control_effectiveness_pct / 100)
    
    # Calculate residual values (round to nearest integer, minimum 1)
    residual_likelihood = max(1, round(inherent_likelihood * effectiveness_factor))
    
    # Impact typically doesn't change much with controls (controls reduce occurrence, not impact)
    # However, some controls can reduce impact through early detection/response
    residual_impact = max(1, round(inherent_impact * (1 - (control_effectiveness_pct / 200))))  # Half effect on impact
    
    residual_score = residual_likelihood * residual_impact
    
    return residual_likelihood, residual_impact, residual_score


def calculate_control_effectiveness_from_linked_controls(risk):
    """
    Calculate overall control effectiveness from linked controls.
    
    Args:
        risk: Risk instance with related controls
    
    Returns:
        int: Aggregate control effectiveness percentage (0-100)
    """
    from compliance.models import ControlImplementation
    
    if not risk.controls.exists():
        return 0
    
    total_effectiveness = 0
    control_count = 0
    
    for control in risk.controls.all():
        # Get implementation for the risk's organization
        impl = ControlImplementation.objects.filter(
            organization=risk.organization,
            control=control
        ).first()
        
        if impl and impl.effectiveness_rating:
            # Convert 1-5 effectiveness to percentage
            # 5 = 100%, 4 = 80%, 3 = 60%, 2 = 40%, 1 = 20%
            total_effectiveness += impl.effectiveness_rating * 20
            control_count += 1
    
    if control_count == 0:
        return 0
    
    # Average effectiveness, capped at 95% (no control is perfect)
    avg_effectiveness = min(95, total_effectiveness / control_count)
    return round(avg_effectiveness)


def check_risk_appetite(risk, appetite_threshold):
    """
    Check if risk exceeds organization's risk appetite.
    
    Args:
        risk: Risk instance
        appetite_threshold: Maximum acceptable risk score
    
    Returns:
        dict: {
            'within_appetite': bool,
            'inherent_exceeds': bool,
            'residual_exceeds': bool,
            'message': str
        }
    """
    inherent_score = risk.inherent_risk_score
    residual_score = risk.residual_risk_score
    
    result = {
        'within_appetite': True,
        'inherent_exceeds': False,
        'residual_exceeds': False,
        'message': 'Risk is within appetite'
    }
    
    if inherent_score and inherent_score > appetite_threshold:
        result['inherent_exceeds'] = True
    
    if residual_score and residual_score > appetite_threshold:
        result['within_appetite'] = False
        result['residual_exceeds'] = True
        result['message'] = f'Residual risk ({residual_score}) exceeds appetite threshold ({appetite_threshold})'
    elif inherent_score and not residual_score and inherent_score > appetite_threshold:
        result['within_appetite'] = False
        result['message'] = f'Inherent risk ({inherent_score}) exceeds appetite threshold ({appetite_threshold}). Controls needed.'
    
    return result


def get_treatment_recommendation(inherent_score, residual_score=None, cost_threshold=None):
    """
    Recommend risk treatment option based on risk scores.
    
    Args:
        inherent_score: Inherent risk score
        residual_score: Residual risk score (after controls)
        cost_threshold: Maximum cost for treatment
    
    Returns:
        str: Recommended treatment option
    """
    score = residual_score or inherent_score
    
    if score is None:
        return 'assess'
    
    if score <= 4:
        return 'accept'  # Low risk - can accept
    elif score <= 9:
        return 'mitigate'  # Medium risk - implement controls
    elif score <= 15:
        return 'mitigate'  # High risk - prioritize mitigation
    else:
        return 'avoid'  # Critical risk - consider avoiding the activity


def aggregate_risks_by_category(risks):
    """
    Aggregate risk statistics by category.
    
    Args:
        risks: QuerySet of Risk objects
    
    Returns:
        dict: Aggregated statistics
    """
    from collections import defaultdict
    
    stats = defaultdict(lambda: {
        'count': 0,
        'total_inherent_score': 0,
        'total_residual_score': 0,
        'critical_count': 0,
        'high_count': 0,
        'medium_count': 0,
        'low_count': 0,
    })
    
    for risk in risks:
        category_name = risk.category.name if risk.category else 'Uncategorized'
        stats[category_name]['count'] += 1
        
        inherent_score = risk.inherent_risk_score or 0
        residual_score = risk.residual_risk_score or inherent_score
        
        stats[category_name]['total_inherent_score'] += inherent_score
        stats[category_name]['total_residual_score'] += residual_score
        
        level = get_risk_level(inherent_score)
        stats[category_name][f'{level}_count'] += 1
    
    return dict(stats)
