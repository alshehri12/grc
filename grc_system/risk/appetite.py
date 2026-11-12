"""
Risk appetite evaluation.

Appetite is the residual risk score the organization is willing to carry;
tolerance is the hard ceiling above which the risk must be escalated.
Statements are defined per risk category with an organization-wide default
(RiskAppetite with category=None). When nothing is defined, the setting
`risk_appetite_threshold` (default 12) and the "critical" matrix threshold
act as appetite and tolerance respectively.
"""
from .utils import get_risk_thresholds

DEFAULT_APPETITE = 12

STATUS_WITHIN = 'within'          # score <= appetite
STATUS_TOLERANCE = 'tolerance'    # appetite < score <= tolerance : treatment required
STATUS_BREACH = 'breach'          # score > tolerance : escalate


def _setting_appetite(organization_id):
    try:
        from core.models import Setting
        s = Setting.objects.filter(key='risk_appetite_threshold', organization_id=organization_id).first() \
            or Setting.objects.filter(key='risk_appetite_threshold', organization__isnull=True).first()
        return int(s.value) if s else DEFAULT_APPETITE
    except Exception:
        return DEFAULT_APPETITE


def resolve_appetite(organization_id, category_id=None):
    """Return (appetite_score, tolerance_score, source, statement_or_None)."""
    from .models import RiskAppetite

    qs = RiskAppetite.objects.filter(organization_id=organization_id, is_active=True)
    if category_id:
        stmt = qs.filter(category_id=category_id).first()
        if stmt:
            return stmt.max_acceptable_score, stmt.tolerance_score, 'category', stmt
    stmt = qs.filter(category__isnull=True).first()
    if stmt:
        return stmt.max_acceptable_score, stmt.tolerance_score, 'organization', stmt
    appetite = _setting_appetite(organization_id)
    tolerance = max(appetite, get_risk_thresholds(organization_id)['critical'])
    return appetite, tolerance, 'default', None


def evaluate_appetite(risk):
    """
    Compare the risk's current exposure (residual if assessed, else inherent)
    with the applicable appetite statement.
    """
    appetite, tolerance, source, stmt = resolve_appetite(risk.organization_id, risk.category_id)
    score = risk.residual_risk_score or risk.inherent_risk_score
    basis = 'residual' if risk.residual_risk_score else 'inherent'
    if score <= appetite:
        status = STATUS_WITHIN
    elif score <= tolerance:
        status = STATUS_TOLERANCE
    else:
        status = STATUS_BREACH
    return {
        'status': status,
        'score': score,
        'basis': basis,
        'appetite': appetite,
        'tolerance': tolerance,
        'excess': max(0, score - appetite),
        'source': source,
        'statement_id': stmt.pk if stmt else None,
        'requires_treatment': status != STATUS_WITHIN,
        'requires_escalation': status == STATUS_BREACH,
    }
