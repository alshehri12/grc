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
