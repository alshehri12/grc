"""
Risk Management Utilities - Core GRC logic for risk calculations.

As a Risk Management Specialist, these are the key calculations:
1. Risk Score = Likelihood × Impact (1-25 scale)
2. Residual Risk = Inherent Risk × (1 - Control Effectiveness)
3. Risk Level based on 5x5 matrix
4. Risk Appetite comparison
"""
from django.core.exceptions import ValidationError


# Risk Matrix Configuration (5x5)
RISK_MATRIX = {
    # (likelihood, impact): (score, level, color)
    (1, 1): (1, 'low', '#4CAF50'),
    (1, 2): (2, 'low', '#4CAF50'),
    (1, 3): (3, 'low', '#8BC34A'),
    (1, 4): (4, 'medium', '#FFEB3B'),
    (1, 5): (5, 'medium', '#FFEB3B'),
    (2, 1): (2, 'low', '#4CAF50'),
    (2, 2): (4, 'low', '#8BC34A'),
    (2, 3): (6, 'medium', '#FFEB3B'),
    (2, 4): (8, 'medium', '#FFC107'),
    (2, 5): (10, 'high', '#FF9800'),
    (3, 1): (3, 'low', '#8BC34A'),
    (3, 2): (6, 'medium', '#FFEB3B'),
    (3, 3): (9, 'medium', '#FFC107'),
    (3, 4): (12, 'high', '#FF9800'),
    (3, 5): (15, 'high', '#FF5722'),
    (4, 1): (4, 'medium', '#FFEB3B'),
    (4, 2): (8, 'medium', '#FFC107'),
    (4, 3): (12, 'high', '#FF9800'),
    (4, 4): (16, 'critical', '#F44336'),
    (4, 5): (20, 'critical', '#D32F2F'),
    (5, 1): (5, 'medium', '#FFEB3B'),
    (5, 2): (10, 'high', '#FF9800'),
    (5, 3): (15, 'high', '#FF5722'),
    (5, 4): (20, 'critical', '#D32F2F'),
    (5, 5): (25, 'critical', '#B71C1C'),
}

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

# Risk Level Thresholds
RISK_LEVELS = {
    'low': {'min': 1, 'max': 4, 'color': '#4CAF50', 'action': 'Monitor and review periodically'},
    'medium': {'min': 5, 'max': 9, 'color': '#FFC107', 'action': 'Implement controls within 6 months'},
    'high': {'min': 10, 'max': 15, 'color': '#FF5722', 'action': 'Immediate action required within 3 months'},
    'critical': {'min': 16, 'max': 25, 'color': '#F44336', 'action': 'Escalate to senior management immediately'},
}


def validate_risk_score(value, field_name='score'):
    """Validate that risk likelihood/impact is between 1-5."""
    if value is not None and (value < 1 or value > 5):
        raise ValidationError(f'{field_name} must be between 1 and 5')


def calculate_risk_score(likelihood, impact):
    """
    Calculate risk score from likelihood and impact.
    
    Args:
        likelihood: 1-5 scale
        impact: 1-5 scale
    
    Returns:
        int: Risk score (1-25)
    """
    if likelihood is None or impact is None:
        return None
    return likelihood * impact


def get_risk_level(score):
    """
    Get risk level from score.
    
    Args:
        score: Risk score (1-25)
    
    Returns:
        str: Risk level (low, medium, high, critical)
    """
    if score is None:
        return None
    
    for level, config in RISK_LEVELS.items():
        if config['min'] <= score <= config['max']:
            return level
    return 'critical' if score > 25 else 'low'


def get_risk_color(score):
    """Get color code for risk score visualization."""
    level = get_risk_level(score)
    return RISK_LEVELS.get(level, {}).get('color', '#9E9E9E')


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
