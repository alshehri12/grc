"""
BCM (Business Continuity Management) Utilities - Core BCM calculations.

As a BCM Specialist, these are the key concepts:
1. RTO (Recovery Time Objective): Max time to restore function
2. RPO (Recovery Point Objective): Max acceptable data loss
3. MTPD (Maximum Tolerable Period of Disruption): Beyond this, business fails
4. RTO must ALWAYS be <= MTPD

Key BIA Logic:
- Higher impact at shorter time = More critical function
- RTO should be set before impact becomes unacceptable
"""
from django.core.exceptions import ValidationError


# Impact Level Configuration
IMPACT_LEVELS = {
    1: {'en': 'Minimal', 'ar': 'الحد الأدنى', 'description': 'No significant impact'},
    2: {'en': 'Low', 'ar': 'منخفض', 'description': 'Minor inconvenience'},
    3: {'en': 'Medium', 'ar': 'متوسط', 'description': 'Noticeable operational impact'},
    4: {'en': 'High', 'ar': 'عالي', 'description': 'Significant business impact'},
    5: {'en': 'Critical', 'ar': 'حرج', 'description': 'Severe/catastrophic impact'},
}

# Criticality to RTO Mapping (recommended maximums in hours)
CRITICALITY_RTO_MAPPING = {
    'critical': 4,      # 4 hours max
    'essential': 24,    # 24 hours (1 day)
    'necessary': 72,    # 72 hours (3 days)
    'desirable': 168,   # 168 hours (1 week)
}

# Impact to recommended MTPD mapping (when impact becomes unacceptable)
IMPACT_TO_MTPD = {
    # If impact reaches level 5 at X hours, MTPD should be less than X hours
    '1_hour': {'impact_threshold': 5, 'recommended_mtpd': 1},
    '4_hours': {'impact_threshold': 5, 'recommended_mtpd': 4},
    '8_hours': {'impact_threshold': 5, 'recommended_mtpd': 8},
    '24_hours': {'impact_threshold': 5, 'recommended_mtpd': 24},
    '72_hours': {'impact_threshold': 5, 'recommended_mtpd': 72},
}


def validate_rto_mtpd(rto_hours, mtpd_hours):
    """
    Validate that RTO is less than or equal to MTPD.
    
    Business Rule: Recovery must happen BEFORE maximum tolerable period!
    
    Args:
        rto_hours: Recovery Time Objective in hours
        mtpd_hours: Maximum Tolerable Period of Disruption in hours
    
    Raises:
        ValidationError: If RTO > MTPD
    """
    if rto_hours is None or mtpd_hours is None:
        return
    
    if rto_hours > mtpd_hours:
        raise ValidationError(
            f'RTO ({rto_hours} hours) cannot exceed MTPD ({mtpd_hours} hours). '
            f'Recovery must happen before maximum tolerable disruption period!'
        )


def validate_rpo_rto(rpo_hours, rto_hours):
    """
    Validate that RPO is less than or equal to RTO.
    
    Business Rule: Data loss point cannot be after recovery time!
    
    Args:
        rpo_hours: Recovery Point Objective in hours
        rto_hours: Recovery Time Objective in hours
    """
    if rpo_hours is None or rto_hours is None:
        return
    
    if rpo_hours > rto_hours:
        raise ValidationError(
            f'RPO ({rpo_hours} hours) should typically not exceed RTO ({rto_hours} hours). '
            f'Review backup strategy to ensure data recovery aligns with service recovery.'
        )


def calculate_recommended_rto(bia):
    """
    Calculate recommended RTO based on BIA impact progression.
    
    Logic: RTO should be set at the point where impact transitions 
    from acceptable (≤3) to unacceptable (>3).
    
    Args:
        bia: BusinessImpactAnalysis instance
    
    Returns:
        int: Recommended RTO in hours
    """
    # Impact thresholds by time
    impacts = [
        (1, bia.impact_1_hour if hasattr(bia, 'impact_1_hour') else 1),
        (4, bia.impact_4_hours if hasattr(bia, 'impact_4_hours') else 2),
        (8, bia.impact_8_hours if hasattr(bia, 'impact_8_hours') else 3),
        (24, bia.impact_24_hours if hasattr(bia, 'impact_24_hours') else 4),
        (72, bia.impact_72_hours if hasattr(bia, 'impact_72_hours') else 5),
    ]
    
    # Find the first point where impact exceeds 3 (unacceptable)
    unacceptable_threshold = 3
    
    for hours, impact in impacts:
        if impact > unacceptable_threshold:
            # RTO should be before this point
            return hours
    
    # If no point exceeds threshold, return 72 hours as default
    return 72


def calculate_recommended_mtpd(bia):
    """
    Calculate recommended MTPD based on BIA impact progression.
    
    Logic: MTPD is when impact reaches critical level (5).
    
    Args:
        bia: BusinessImpactAnalysis instance
    
    Returns:
        int: Recommended MTPD in hours
    """
    impacts = [
        (1, bia.impact_1_hour if hasattr(bia, 'impact_1_hour') else 1),
        (4, bia.impact_4_hours if hasattr(bia, 'impact_4_hours') else 2),
        (8, bia.impact_8_hours if hasattr(bia, 'impact_8_hours') else 3),
        (24, bia.impact_24_hours if hasattr(bia, 'impact_24_hours') else 4),
        (72, bia.impact_72_hours if hasattr(bia, 'impact_72_hours') else 5),
    ]
    
    critical_threshold = 5
    
    for hours, impact in impacts:
        if impact >= critical_threshold:
            return hours
    
    # If never reaches critical, return maximum (1 week)
    return 168


def get_criticality_from_rto(rto_hours):
    """
    Determine function criticality based on RTO.
    
    Args:
        rto_hours: RTO in hours
    
    Returns:
        str: Criticality level
    """
    if rto_hours is None:
        return 'necessary'
    
    if rto_hours <= 4:
        return 'critical'
    elif rto_hours <= 24:
        return 'essential'
    elif rto_hours <= 72:
        return 'necessary'
    else:
        return 'desirable'


def calculate_dependency_impact(business_function):
    """
    Calculate cascading impact from function dependencies.
    
    If a function fails, all dependent functions are impacted.
    
    Args:
        business_function: BusinessFunction instance
    
    Returns:
        dict: {
            'direct_dependents': list of function names,
            'total_affected': count of all affected functions,
            'max_criticality': highest criticality in chain,
            'cascade_depth': how many levels of dependencies
        }
    """
    from bcm.models import BusinessFunction
    
    visited = set()
    affected_functions = []
    max_criticality_level = 0
    
    criticality_ranking = {
        'desirable': 1,
        'necessary': 2,
        'essential': 3,
        'critical': 4,
    }
    
    def traverse_dependents(func, depth=0):
        nonlocal max_criticality_level
        
        if func.id in visited:
            return depth
        visited.add(func.id)
        
        max_depth = depth
        
        # Get functions that depend on this one
        dependents = BusinessFunction.objects.filter(dependent_functions=func)
        
        for dep in dependents:
            affected_functions.append({
                'id': dep.id,
                'name': dep.name,
                'criticality': dep.criticality,
                'depth': depth + 1
            })
            
            crit_level = criticality_ranking.get(dep.criticality, 0)
            if crit_level > max_criticality_level:
                max_criticality_level = crit_level
            
            child_depth = traverse_dependents(dep, depth + 1)
            max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    cascade_depth = traverse_dependents(business_function)
    
    # Reverse lookup for max criticality
    criticality_names = {v: k for k, v in criticality_ranking.items()}
    
    return {
        'direct_dependents': [f['name'] for f in affected_functions if f['depth'] == 1],
        'all_affected': affected_functions,
        'total_affected': len(affected_functions),
        'max_criticality': criticality_names.get(max_criticality_level, 'desirable'),
        'cascade_depth': cascade_depth,
    }


def validate_bc_plan_coverage(bc_plan):
    """
    Validate that BC Plan covers all critical functions.
    
    Args:
        bc_plan: BCPlan instance
    
    Returns:
        dict: {
            'is_complete': bool,
            'covered_critical': count,
            'uncovered_critical': list of function names,
            'coverage_percentage': float
        }
    """
    from bcm.models import BusinessFunction
    
    # Get all critical/essential functions for the organization
    critical_functions = BusinessFunction.objects.filter(
        organization=bc_plan.organization,
        criticality__in=['critical', 'essential'],
        status='active'
    )
    
    covered_ids = set(bc_plan.covered_functions.values_list('id', flat=True))
    
    uncovered = []
    for func in critical_functions:
        if func.id not in covered_ids:
            uncovered.append({
                'id': func.id,
                'name': func.name,
                'criticality': func.criticality
            })
    
    total_critical = critical_functions.count()
    covered_count = total_critical - len(uncovered)
    coverage_pct = (covered_count / total_critical * 100) if total_critical > 0 else 100
    
    return {
        'is_complete': len(uncovered) == 0,
        'total_critical_functions': total_critical,
        'covered_critical': covered_count,
        'uncovered_critical': uncovered,
        'coverage_percentage': round(coverage_pct, 1)
    }


def check_plan_test_status(bc_plan):
    """
    Check if BC Plan needs testing based on last test date.
    
    Best practice: Plans should be tested at least annually.
    
    Args:
        bc_plan: BCPlan instance
    
    Returns:
        dict: {
            'needs_testing': bool,
            'days_since_last_test': int or None,
            'recommendation': str
        }
    """
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.now().date()
    
    if not bc_plan.last_tested_date:
        return {
            'needs_testing': True,
            'days_since_last_test': None,
            'recommendation': 'Plan has never been tested. Schedule a test immediately.'
        }
    
    days_since_test = (today - bc_plan.last_tested_date).days
    
    if days_since_test > 365:
        return {
            'needs_testing': True,
            'days_since_last_test': days_since_test,
            'recommendation': f'Plan was last tested {days_since_test} days ago. Annual testing required.'
        }
    elif days_since_test > 270:  # 9 months
        return {
            'needs_testing': False,
            'days_since_last_test': days_since_test,
            'recommendation': f'Plan testing due within {365 - days_since_test} days. Schedule soon.'
        }
    else:
        return {
            'needs_testing': False,
            'days_since_last_test': days_since_test,
            'recommendation': f'Plan was tested {days_since_test} days ago. Next test due in {365 - days_since_test} days.'
        }


def calculate_minimum_resources(bia):
    """
    Calculate minimum resources needed for recovery.
    
    Args:
        bia: BusinessImpactAnalysis instance
    
    Returns:
        dict: Resource requirements summary
    """
    return {
        'staff': bia.minimum_staff,
        'equipment': bia.minimum_equipment if bia.minimum_equipment else 'Not specified',
        'systems': bia.system_dependencies if bia.system_dependencies else 'Not specified',
        'vendors': bia.vendor_dependencies if bia.vendor_dependencies else 'Not specified',
    }


# --------------------------------------------------------------------------- #
# Exercise schedule & recovery capability analysis (ISO 22301 8.4 / 8.5)
# --------------------------------------------------------------------------- #
def plan_test_status(plan):
    """
    Test status for a BC or DR plan using its own frequency / next_test_date.
    Returns {'needs_testing', 'overdue', 'next_test_date', 'days_until_due', 'recommendation'}.
    """
    from datetime import timedelta
    from django.utils import timezone

    today = timezone.localdate()
    interval = (plan.test_frequency_months or 12) * 30
    next_due = plan.next_test_date or (plan.last_tested_date + timedelta(days=interval) if plan.last_tested_date else None)
    if next_due is None:
        return {'needs_testing': True, 'overdue': True, 'next_test_date': None, 'days_until_due': None,
                'recommendation': 'Plan has never been tested. Schedule an exercise immediately.'}
    days = (next_due - today).days
    if days < 0:
        rec = f'Test is {-days} days overdue. Schedule an exercise immediately.'
    elif days <= 90:
        rec = f'Test due in {days} days. Schedule soon.'
    else:
        rec = f'Next test due on {next_due:%Y-%m-%d}.'
    return {'needs_testing': days <= 90, 'overdue': days < 0, 'next_test_date': next_due,
            'days_until_due': days, 'recommendation': rec}


CAPABILITY_STATUS_ORDER = ['no_bia', 'no_dependencies', 'no_dr_plan', 'gap', 'unproven', 'untested', 'covered']


def capability_analysis(organization, functions=None, test_interval_days=365):
    """
    Compare what the business NEEDS (BIA: RTO/RPO/MTPD) with what IT CAN DELIVER
    (DR plans: achievable RTO/RPO, proven by the latest exercise).

    Returns {'summary': {...}, 'functions': [ {...per function...} ]}
    Per-function status (worst wins):
      no_bia          - no completed/approved BIA with an RTO
      no_dependencies - BIA/function name no systems, so capability cannot be assessed
      no_dr_plan      - at least one dependent system has no approved/active DR plan
      gap             - a DR plan's achievable RTO/RPO is worse than the BIA requirement
      unproven        - the latest exercise did not meet the required RTO
      untested        - no exercise with a measured RTO in the last `test_interval_days`
      covered         - requirement met and proven by a recent exercise
    """
    from datetime import timedelta
    from django.utils import timezone
    from bcm.models import BusinessFunction, DisasterRecoveryPlan, BCMTest

    today = timezone.localdate()
    recent_cutoff = today - timedelta(days=test_interval_days)

    if functions is None:
        functions = BusinessFunction.objects.filter(organization=organization, status='active')
    functions = functions.select_related('owner', 'department').prefetch_related('related_assets')

    live_plans = DisasterRecoveryPlan.objects.filter(organization=organization, status__in=['approved', 'active']) \
        .prefetch_related('covered_assets').select_related('owner')
    plans_by_asset = {}
    for plan in live_plans:
        for asset in plan.covered_assets.all():
            plans_by_asset.setdefault(asset.pk, []).append(plan)

    # Latest completed exercise with a measured RTO per DR plan
    latest_test = {}
    for t in BCMTest.objects.filter(organization=organization, status='completed', dr_plan__isnull=False,
                                    achieved_rto_hours__isnull=False).order_by('dr_plan_id', '-actual_end', '-scheduled_date'):
        latest_test.setdefault(t.dr_plan_id, t)

    results = []
    for fn in functions:
        bia = fn.bias.filter(status__in=['completed', 'approved']).order_by('-assessment_date', '-id') \
            .prefetch_related('dependent_assets').first()
        row = {
            'function': {'id': fn.pk, 'function_id': fn.function_id, 'name': fn.name, 'name_ar': fn.name_ar,
                         'criticality': fn.criticality, 'owner': fn.owner.get_full_name() if fn.owner else None,
                         'owner_id': fn.owner_id, 'department_id': fn.department_id},
            'required': None, 'achievable': None, 'proven': None, 'assets': [], 'status': None, 'issues': [],
        }
        if not bia or bia.rto_hours is None:
            row['status'] = 'no_bia'
            row['issues'].append('No completed BIA with an RTO')
            results.append(row)
            continue

        row['required'] = {'rto_hours': bia.rto_hours, 'rpo_hours': bia.rpo_hours, 'mtpd_hours': bia.mtpd_hours,
                           'bia_id': bia.pk, 'assessment_date': bia.assessment_date}
        assets = {a.pk: a for a in bia.dependent_assets.all()}
        assets.update({a.pk: a for a in fn.related_assets.all()})
        if not assets:
            row['status'] = 'no_dependencies'
            row['issues'].append('No dependent systems linked to the BIA or function')
            results.append(row)
            continue

        statuses = set()
        worst_rto = worst_rpo = 0
        proven_rto = None
        proven_recent = True
        for asset in assets.values():
            plans = plans_by_asset.get(asset.pk, [])
            a_row = {'asset_id': asset.asset_id, 'name': asset.name, 'id': asset.pk, 'plans': []}
            if not plans:
                a_row['status'] = 'no_dr_plan'
                statuses.add('no_dr_plan')
                row['issues'].append(f'{asset.name}: no approved DR plan covers this system')
            else:
                a_status = 'covered'
                best_rto = min((p.achievable_rto_hours for p in plans if p.achievable_rto_hours is not None), default=None)
                best_rpo = min((p.achievable_rpo_hours for p in plans if p.achievable_rpo_hours is not None), default=None)
                for p in plans:
                    t = latest_test.get(p.pk)
                    a_row['plans'].append({
                        'id': p.pk, 'plan_id': p.plan_id, 'title': p.title, 'owner_id': p.owner_id,
                        'achievable_rto_hours': p.achievable_rto_hours, 'achievable_rpo_hours': p.achievable_rpo_hours,
                        'last_tested_date': p.last_tested_date, 'next_test_date': p.next_test_date,
                        'last_test': {'test_id': t.test_id, 'date': (t.actual_end or t.scheduled_date),
                                      'achieved_rto_hours': float(t.achieved_rto_hours),
                                      'achieved_rpo_hours': float(t.achieved_rpo_hours) if t.achieved_rpo_hours is not None else None,
                                      'result': t.overall_result} if t else None,
                    })
                if best_rto is None:
                    a_status = 'gap'
                    row['issues'].append(f'{asset.name}: DR plan has no achievable RTO defined')
                else:
                    worst_rto = max(worst_rto, best_rto)
                    if best_rto > bia.rto_hours:
                        a_status = 'gap'
                        row['issues'].append(f'{asset.name}: achievable RTO {best_rto}h exceeds required {bia.rto_hours}h')
                if best_rpo is not None and bia.rpo_hours is not None:
                    worst_rpo = max(worst_rpo, best_rpo)
                    if best_rpo > bia.rpo_hours:
                        a_status = 'gap'
                        row['issues'].append(f'{asset.name}: achievable RPO {best_rpo}h exceeds required {bia.rpo_hours}h')
                # proof by exercise
                tests = [latest_test.get(p.pk) for p in plans if latest_test.get(p.pk)]
                if not tests:
                    proven_recent = False
                    if a_status == 'covered':
                        a_status = 'untested'
                        row['issues'].append(f'{asset.name}: no exercise has measured the recovery time')
                else:
                    best = min(tests, key=lambda t: t.achieved_rto_hours)
                    tested_on = (best.actual_end.date() if best.actual_end else best.scheduled_date)
                    achieved = float(best.achieved_rto_hours)
                    proven_rto = max(proven_rto or 0, achieved)
                    if tested_on < recent_cutoff:
                        proven_recent = False
                        if a_status == 'covered':
                            a_status = 'untested'
                            row['issues'].append(f'{asset.name}: last measured exercise was on {tested_on:%Y-%m-%d} (older than {test_interval_days} days)')
                    elif achieved > bia.rto_hours and a_status == 'covered':
                        a_status = 'unproven'
                        row['issues'].append(f'{asset.name}: last exercise achieved {achieved:g}h against a required {bia.rto_hours}h')
                statuses.add(a_status)
            row['assets'].append(a_row)

        row['achievable'] = {'rto_hours': worst_rto if worst_rto else None, 'rpo_hours': worst_rpo if worst_rpo else None}
        row['proven'] = {'rto_hours': proven_rto, 'recent': proven_recent}
        row['status'] = next(s for s in CAPABILITY_STATUS_ORDER if s in statuses)
        results.append(row)

    summary = {s: 0 for s in CAPABILITY_STATUS_ORDER}
    for r in results:
        summary[r['status']] += 1
    summary['total'] = len(results)
    summary['critical_at_risk'] = sum(1 for r in results if r['function']['criticality'] in ('critical', 'essential')
                                      and r['status'] != 'covered')
    return {'summary': summary, 'functions': results}
