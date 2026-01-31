"""
Compliance Management Utilities - Core compliance calculations.

Key GRC Compliance Concepts:
1. Control Implementation Status tracking
2. Maturity Level assessment (0-5 scale)
3. Gap Assessment calculations
4. Compliance Score computation
"""
from django.db.models import Avg, Count, Q
from django.utils import timezone


# Maturity Level Definitions (CMMI-based)
MATURITY_LEVELS = {
    0: {
        'name': 'Non-existent',
        'name_ar': 'غير موجود',
        'description': 'No process or control exists',
        'color': '#B71C1C'
    },
    1: {
        'name': 'Initial/Ad-hoc',
        'name_ar': 'أولي',
        'description': 'Process is ad-hoc and chaotic',
        'color': '#F44336'
    },
    2: {
        'name': 'Managed',
        'name_ar': 'مُدار',
        'description': 'Process is documented and repeatable',
        'color': '#FF9800'
    },
    3: {
        'name': 'Defined',
        'name_ar': 'محدد',
        'description': 'Process is standardized and consistent',
        'color': '#FFC107'
    },
    4: {
        'name': 'Quantitatively Managed',
        'name_ar': 'مُدار كمياً',
        'description': 'Process is measured and controlled',
        'color': '#8BC34A'
    },
    5: {
        'name': 'Optimizing',
        'name_ar': 'محسّن',
        'description': 'Continuous improvement based on metrics',
        'color': '#4CAF50'
    },
}

# Implementation Status Weights for scoring
STATUS_WEIGHTS = {
    'implemented': 100,
    'partially_implemented': 50,
    'in_progress': 25,
    'planned': 10,
    'not_implemented': 0,
    'not_applicable': None,  # Excluded from scoring
}


def calculate_compliance_score(organization, framework=None):
    """
    Calculate overall compliance score for an organization.
    
    Formula: (Fully Implemented × 100 + Partially × 50) / Total Applicable Controls
    
    Args:
        organization: Organization instance
        framework: Optional framework to filter by
    
    Returns:
        dict: {
            'score': float (0-100),
            'total_controls': int,
            'implemented': int,
            'partially_implemented': int,
            'in_progress': int,
            'not_implemented': int,
            'not_applicable': int,
            'by_domain': dict
        }
    """
    from compliance.models import ControlImplementation, Control
    
    impls = ControlImplementation.objects.filter(organization=organization)
    
    if framework:
        impls = impls.filter(control__domain__framework=framework)
    
    stats = impls.aggregate(
        total=Count('id'),
        implemented=Count('id', filter=Q(status='implemented')),
        partially=Count('id', filter=Q(status='partially_implemented')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        planned=Count('id', filter=Q(status='planned')),
        not_impl=Count('id', filter=Q(status='not_implemented')),
        na=Count('id', filter=Q(status='not_applicable')),
    )
    
    applicable = stats['total'] - stats['na']
    
    if applicable > 0:
        weighted_score = (
            stats['implemented'] * 100 +
            stats['partially'] * 50 +
            stats['in_progress'] * 25 +
            stats['planned'] * 10
        ) / applicable
    else:
        weighted_score = 0
    
    # Calculate by domain
    domain_scores = {}
    domain_impls = impls.values(
        'control__domain__code',
        'control__domain__name'
    ).annotate(
        total=Count('id'),
        implemented=Count('id', filter=Q(status='implemented')),
        partially=Count('id', filter=Q(status='partially_implemented')),
        na=Count('id', filter=Q(status='not_applicable')),
    )
    
    for d in domain_impls:
        domain_applicable = d['total'] - d['na']
        if domain_applicable > 0:
            domain_score = (d['implemented'] * 100 + d['partially'] * 50) / domain_applicable
        else:
            domain_score = 0
        
        domain_scores[d['control__domain__code']] = {
            'name': d['control__domain__name'],
            'score': round(domain_score, 1),
            'total': d['total'],
            'implemented': d['implemented']
        }
    
    return {
        'score': round(weighted_score, 1),
        'total_controls': stats['total'],
        'implemented': stats['implemented'],
        'partially_implemented': stats['partially'],
        'in_progress': stats['in_progress'],
        'planned': stats['planned'],
        'not_implemented': stats['not_impl'],
        'not_applicable': stats['na'],
        'applicable': applicable,
        'by_domain': domain_scores
    }


def calculate_maturity_score(organization, framework=None):
    """
    Calculate average maturity level for an organization.
    
    Args:
        organization: Organization instance
        framework: Optional framework to filter by
    
    Returns:
        dict: {
            'average_maturity': float,
            'maturity_level': str,
            'distribution': dict
        }
    """
    from compliance.models import ControlImplementation
    
    impls = ControlImplementation.objects.filter(organization=organization)
    
    if framework:
        impls = impls.filter(control__domain__framework=framework)
    
    # Exclude N/A controls
    impls = impls.exclude(status='not_applicable')
    
    if not impls.exists():
        return {
            'average_maturity': 0,
            'maturity_level': 'Non-existent',
            'distribution': {i: 0 for i in range(6)}
        }
    
    avg_maturity = impls.aggregate(avg=Avg('maturity_level'))['avg'] or 0
    
    # Distribution
    distribution = {}
    for level in range(6):
        count = impls.filter(maturity_level=level).count()
        distribution[level] = count
    
    # Determine overall level
    rounded_level = round(avg_maturity)
    maturity_info = MATURITY_LEVELS.get(rounded_level, MATURITY_LEVELS[0])
    
    return {
        'average_maturity': round(avg_maturity, 2),
        'maturity_level': maturity_info['name'],
        'maturity_level_ar': maturity_info['name_ar'],
        'distribution': distribution,
        'color': maturity_info['color']
    }


def auto_calculate_gap_assessment(gap_assessment):
    """
    Automatically calculate gap assessment results from control implementations.
    
    Args:
        gap_assessment: GapAssessment instance
    
    Returns:
        dict: Updated statistics
    """
    from compliance.models import ControlImplementation, Control
    
    # Get all controls for this framework
    controls = Control.objects.filter(domain__framework=gap_assessment.framework)
    
    # Get implementations for this organization
    impls = ControlImplementation.objects.filter(
        organization=gap_assessment.organization,
        control__domain__framework=gap_assessment.framework
    )
    
    impl_stats = impls.aggregate(
        implemented=Count('id', filter=Q(status='implemented')),
        partially=Count('id', filter=Q(status='partially_implemented')),
        not_impl=Count('id', filter=Q(status='not_implemented')),
        na=Count('id', filter=Q(status='not_applicable')),
        avg_maturity=Avg('maturity_level')
    )
    
    total_controls = controls.count()
    
    # Update gap assessment
    gap_assessment.total_controls = total_controls
    gap_assessment.implemented_controls = impl_stats['implemented']
    gap_assessment.partially_implemented = impl_stats['partially']
    gap_assessment.not_implemented = impl_stats['not_impl']
    gap_assessment.not_applicable = impl_stats['na']
    
    # Calculate compliance score
    applicable = total_controls - impl_stats['na']
    if applicable > 0:
        gap_assessment.compliance_score = round(
            (impl_stats['implemented'] * 100 + impl_stats['partially'] * 50) / applicable,
            2
        )
    else:
        gap_assessment.compliance_score = 0
    
    # Maturity score
    gap_assessment.maturity_score = round(impl_stats['avg_maturity'] or 0, 2)
    
    gap_assessment.save()
    
    return {
        'total_controls': total_controls,
        'implemented': impl_stats['implemented'],
        'partially_implemented': impl_stats['partially'],
        'not_implemented': impl_stats['not_impl'],
        'not_applicable': impl_stats['na'],
        'compliance_score': gap_assessment.compliance_score,
        'maturity_score': gap_assessment.maturity_score
    }


def identify_gaps(organization, framework):
    """
    Identify control gaps for an organization.
    
    Args:
        organization: Organization instance
        framework: Framework to assess
    
    Returns:
        list: List of gap details
    """
    from compliance.models import ControlImplementation, Control
    
    gaps = []
    
    # Get all controls in framework
    controls = Control.objects.filter(domain__framework=framework)
    
    for control in controls:
        impl = ControlImplementation.objects.filter(
            organization=organization,
            control=control
        ).first()
        
        if not impl:
            # No implementation record - gap
            gaps.append({
                'control_id': control.control_id,
                'control_title': control.title,
                'domain': control.domain.name if control.domain else 'Unknown',
                'gap_type': 'not_assessed',
                'severity': 'high',
                'recommendation': 'Create implementation record and assess control'
            })
        elif impl.status == 'not_implemented':
            gaps.append({
                'control_id': control.control_id,
                'control_title': control.title,
                'domain': control.domain.name if control.domain else 'Unknown',
                'gap_type': 'not_implemented',
                'severity': 'high',
                'gap_description': impl.gap_description,
                'remediation_plan': impl.remediation_plan,
                'target_date': impl.target_date,
                'recommendation': 'Implement control as per remediation plan'
            })
        elif impl.status == 'partially_implemented':
            gaps.append({
                'control_id': control.control_id,
                'control_title': control.title,
                'domain': control.domain.name if control.domain else 'Unknown',
                'gap_type': 'partially_implemented',
                'severity': 'medium',
                'gap_description': impl.gap_description,
                'remediation_plan': impl.remediation_plan,
                'target_date': impl.target_date,
                'recommendation': 'Complete implementation as per plan'
            })
        elif impl.maturity_level < 3:
            gaps.append({
                'control_id': control.control_id,
                'control_title': control.title,
                'domain': control.domain.name if control.domain else 'Unknown',
                'gap_type': 'maturity_gap',
                'severity': 'low',
                'current_maturity': impl.maturity_level,
                'recommendation': f'Improve maturity from level {impl.maturity_level} to at least level 3'
            })
    
    # Sort by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    gaps.sort(key=lambda x: severity_order.get(x['severity'], 3))
    
    return gaps


def check_evidence_status(organization):
    """
    Check evidence status - identify expired or expiring evidence.
    
    Args:
        organization: Organization instance
    
    Returns:
        dict: Evidence status summary
    """
    from compliance.models import Evidence
    from datetime import timedelta
    
    today = timezone.now().date()
    expiring_threshold = today + timedelta(days=30)
    
    all_evidence = Evidence.objects.filter(organization=organization)
    
    expired = all_evidence.filter(valid_until__lt=today, status__in=['accepted', 'submitted'])
    expiring_soon = all_evidence.filter(
        valid_until__gte=today,
        valid_until__lte=expiring_threshold,
        status__in=['accepted', 'submitted']
    )
    
    return {
        'total_evidence': all_evidence.count(),
        'accepted_count': all_evidence.filter(status='accepted').count(),
        'expired_count': expired.count(),
        'expired_evidence': list(expired.values('evidence_id', 'title', 'valid_until')),
        'expiring_soon_count': expiring_soon.count(),
        'expiring_evidence': list(expiring_soon.values('evidence_id', 'title', 'valid_until')),
    }


def calculate_control_effectiveness(control_implementation):
    """
    Calculate control effectiveness based on multiple factors.
    
    Factors:
    - Implementation status
    - Maturity level
    - Last test date (if tested recently)
    - Number of related findings
    
    Args:
        control_implementation: ControlImplementation instance
    
    Returns:
        dict: {
            'effectiveness_score': int (0-100),
            'factors': dict
        }
    """
    from compliance.models import AuditFinding
    
    factors = {}
    total_weight = 0
    weighted_score = 0
    
    # Factor 1: Implementation Status (weight: 40%)
    status_scores = {
        'implemented': 100,
        'partially_implemented': 50,
        'in_progress': 25,
        'planned': 10,
        'not_implemented': 0,
    }
    status_score = status_scores.get(control_implementation.status, 0)
    factors['implementation_status'] = {'score': status_score, 'weight': 40}
    weighted_score += status_score * 40
    total_weight += 40
    
    # Factor 2: Maturity Level (weight: 30%)
    maturity_score = (control_implementation.maturity_level / 5) * 100
    factors['maturity'] = {'score': maturity_score, 'weight': 30}
    weighted_score += maturity_score * 30
    total_weight += 30
    
    # Factor 3: Testing Recency (weight: 15%)
    if control_implementation.last_tested_date:
        from datetime import date
        days_since_test = (date.today() - control_implementation.last_tested_date).days
        if days_since_test <= 90:
            test_score = 100
        elif days_since_test <= 180:
            test_score = 75
        elif days_since_test <= 365:
            test_score = 50
        else:
            test_score = 25
    else:
        test_score = 0
    factors['testing'] = {'score': test_score, 'weight': 15}
    weighted_score += test_score * 15
    total_weight += 15
    
    # Factor 4: Open Findings (weight: 15%)
    open_findings = AuditFinding.objects.filter(
        control=control_implementation.control,
        status__in=['open', 'in_progress']
    ).count()
    if open_findings == 0:
        findings_score = 100
    elif open_findings <= 2:
        findings_score = 60
    else:
        findings_score = 20
    factors['findings'] = {'score': findings_score, 'weight': 15, 'open_count': open_findings}
    weighted_score += findings_score * 15
    total_weight += 15
    
    effectiveness = round(weighted_score / total_weight) if total_weight > 0 else 0
    
    return {
        'effectiveness_score': effectiveness,
        'factors': factors
    }


def get_audit_statistics(organization):
    """
    Get audit statistics for an organization.
    
    Args:
        organization: Organization instance
    
    Returns:
        dict: Audit statistics
    """
    from compliance.models import Audit, AuditFinding
    
    audits = Audit.objects.filter(organization=organization)
    findings = AuditFinding.objects.filter(audit__organization=organization)
    
    return {
        'total_audits': audits.count(),
        'completed_audits': audits.filter(status='completed').count(),
        'in_progress_audits': audits.filter(status__in=['in_progress', 'fieldwork', 'reporting']).count(),
        'planned_audits': audits.filter(status='planned').count(),
        'total_findings': findings.count(),
        'open_findings': findings.filter(status='open').count(),
        'critical_findings': findings.filter(finding_type='major_nc', status='open').count(),
        'overdue_findings': findings.filter(
            status__in=['open', 'in_progress'],
            due_date__lt=timezone.now().date()
        ).count(),
    }
