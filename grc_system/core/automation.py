"""
GRC automation jobs.

Every recurring piece of GRC housekeeping lives here as a plain function so
it can run from three places:

  * Celery beat (production)      -> workflow/tasks.py wraps each job
  * `python manage.py run_automation` (cron / local / demo)
  * tests                          -> call the functions directly

Jobs are idempotent: running them twice in a row produces no duplicate
notifications (see `notify_once`).
"""
import logging
from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger('grc.automation')

DEFAULTS = {
    'REVIEW_WARNING_DAYS': 30,        # policies, procedures, plans, control tests
    'RISK_REVIEW_WARNING_DAYS': 14,
    'EVIDENCE_WARNING_DAYS': 30,
    'ACCEPTANCE_WARNING_DAYS': 30,
    'PLAN_TEST_INTERVAL_DAYS': 365,   # BC/DR plans must be exercised at least annually
    'BIA_REVIEW_INTERVAL_DAYS': 365,
    'UPCOMING_EVENT_DAYS': 7,         # audits / BCM tests starting soon
    'REMINDER_DEDUPE_DAYS': 7,        # don't repeat the same reminder more often than this
    'EMAIL_ENABLED': True,
}


def conf(key):
    return getattr(settings, 'GRC_AUTOMATION', {}).get(key, DEFAULTS[key])


def today():
    return timezone.localdate()


# --------------------------------------------------------------------------- #
# Notification helper
# --------------------------------------------------------------------------- #
def notify_once(recipient, subject, body, content_type='', object_id=None,
                priority='normal', dedupe_days=None, template_event=None):
    """
    Create an in-app notification unless an identical one (same recipient,
    object and subject) was created within `dedupe_days`. Returns the
    Notification or None. Email delivery happens in `deliver_notifications`.
    """
    from notifications.models import Notification, NotificationTemplate

    if recipient is None or not getattr(recipient, 'is_active', True):
        return None
    window = timezone.now() - timedelta(days=dedupe_days if dedupe_days is not None else conf('REMINDER_DEDUPE_DAYS'))
    exists = Notification.objects.filter(
        recipient=recipient, subject=subject[:300], content_type=content_type,
        object_id=object_id, created_at__gte=window,
    ).exists()
    if exists:
        return None
    template = None
    if template_event:
        template = NotificationTemplate.objects.filter(event_type=template_event, is_active=True).first()
    return Notification.objects.create(
        template=template, recipient=recipient, subject=subject[:300], body=body,
        channel='in_app', priority=priority, status='pending',
        content_type=content_type, object_id=object_id,
    )


def _recipients(*users):
    seen, out = set(), []
    for u in users:
        if u and u.pk not in seen:
            seen.add(u.pk)
            out.append(u)
    return out


def _dept_manager(obj):
    dept = getattr(obj, 'department', None)
    return dept.manager if dept and dept.manager_id else None


def _ct(obj):
    return f'{obj._meta.app_label}.{obj._meta.model_name}'


# --------------------------------------------------------------------------- #
# 1. Workflow SLA: escalations, approval reminders, overdue tasks
# --------------------------------------------------------------------------- #
def escalate_overdue_approvals():
    """Escalate pending approvals that breached their SLA (via WorkflowService)."""
    from workflow.models import Approval
    from workflow.services import WorkflowService

    overdue = Approval.objects.filter(status='pending', due_date__lt=timezone.now()) \
        .select_related('workflow_instance__template', 'step', 'assignee')
    escalated = 0
    for approval in overdue:
        try:
            if WorkflowService.check_and_escalate(approval.workflow_instance):
                escalated += 1
            if approval.assignee:
                notify_once(approval.assignee, f'OVERDUE approval: {approval.workflow_instance.object_title}',
                            f"The approval step '{approval.step.name}' was due on "
                            f"{approval.due_date:%Y-%m-%d}. Please action it now.",
                            'workflow.approval', approval.pk, priority='urgent', template_event='task_overdue')
        except Exception:
            logger.exception('Error escalating approval %s', approval.pk)
    return {'overdue': overdue.count(), 'escalated': escalated}


def remind_upcoming_approvals():
    """Remind approvers 24h before an approval is due."""
    from workflow.models import Approval, WorkflowHistory

    now = timezone.now()
    upcoming = Approval.objects.filter(status='pending', due_date__gte=now, due_date__lte=now + timedelta(days=1)) \
        .select_related('workflow_instance__template', 'step', 'assignee')
    sent = 0
    for approval in upcoming:
        if not approval.assignee:
            continue
        n = notify_once(approval.assignee, f'Reminder: approval due tomorrow - {approval.workflow_instance.object_title}',
                        f"Workflow: {approval.workflow_instance.template.name}\nItem: {approval.workflow_instance.object_title}\n"
                        f"Step: {approval.step.name}\nDue: {approval.due_date:%Y-%m-%d %H:%M}\n\n"
                        "Please take action before the deadline to avoid escalation.",
                        'workflow.approval', approval.pk, priority='high', dedupe_days=1, template_event='task_due')
        if n:
            sent += 1
            WorkflowHistory.objects.create(workflow_instance=approval.workflow_instance, action='reminder_sent',
                                           details=f'Reminder sent to {approval.assignee.get_full_name() or approval.assignee.username}',
                                           step_number=approval.step.order)
    return {'reminders_sent': sent}


def process_escalations():
    """Notify the escalation target for every pending escalation and mark it escalated."""
    from notifications.models import Escalation

    processed = 0
    for esc in Escalation.objects.filter(status='pending').select_related('escalated_from', 'escalated_to'):
        if esc.escalated_to:
            notify_once(esc.escalated_to, f'Escalation: {esc.object_title}',
                        f"An item has been escalated to you due to an SLA breach.\n\nItem: {esc.object_title}\n"
                        f"Reason: {esc.reason}\nLevel: {esc.level}\nOriginally assigned to: "
                        f"{esc.escalated_from.get_full_name() if esc.escalated_from else 'Unknown'}",
                        esc.content_type, esc.object_id, priority='urgent', dedupe_days=1, template_event='escalation')
        esc.status = 'escalated'
        esc.save(update_fields=['status'])
        processed += 1
    return {'processed': processed}


def mark_overdue_items():
    """Flag overdue tasks, corrective actions and audit findings, and tell their owners."""
    from workflow.models import Task
    from compliance.models import CorrectiveAction, AuditFinding

    now, day = timezone.now(), today()
    results = {}

    tasks = Task.objects.filter(status__in=['pending', 'in_progress'], due_date__lt=now).select_related('assigned_to')
    for t in tasks:
        notify_once(t.assigned_to, f'OVERDUE task: {t.title}', f"Task '{t.title}' was due on {t.due_date:%Y-%m-%d}.",
                    'workflow.task', t.pk, priority='high', template_event='task_overdue')
    results['tasks'] = tasks.update(status='overdue')

    # due tomorrow
    for t in Task.objects.filter(status__in=['pending', 'in_progress'], due_date__gte=now,
                                 due_date__lte=now + timedelta(days=1)).select_related('assigned_to'):
        notify_once(t.assigned_to, f'Task due tomorrow: {t.title}', f"Task '{t.title}' is due on {t.due_date:%Y-%m-%d}.",
                    'workflow.task', t.pk, priority='normal', dedupe_days=1, template_event='task_due')

    cars = CorrectiveAction.objects.filter(status__in=['open', 'in_progress'], target_date__lt=day).select_related('owner')
    for c in cars:
        for u in _recipients(c.owner, c.created_by):
            notify_once(u, f'OVERDUE corrective action: {c.car_id}', f"'{c.title}' was due on {c.target_date:%Y-%m-%d}.",
                        'compliance.correctiveaction', c.pk, priority='high', template_event='task_overdue')
    results['corrective_actions'] = cars.update(status='overdue')

    findings = AuditFinding.objects.filter(status__in=['open', 'in_progress'], due_date__lt=day).select_related('assigned_to')
    for f in findings:
        for u in _recipients(f.assigned_to, _dept_manager(f)):
            notify_once(u, f'OVERDUE audit finding: {f.finding_id}', f"'{f.title}' was due on {f.due_date:%Y-%m-%d}.",
                        'compliance.auditfinding', f.pk, priority='high', template_event='task_overdue')
    results['findings'] = findings.update(status='overdue')
    return results


# --------------------------------------------------------------------------- #
# 2. Review cycles: policies, risks, plans, controls, BIAs, upcoming events
# --------------------------------------------------------------------------- #
def send_review_reminders():
    from governance.models import Policy, Procedure
    from risk.models import Risk
    from bcm.models import BCPlan, DisasterRecoveryPlan, BusinessImpactAnalysis, BCMTest
    from compliance.models import ControlImplementation, Audit

    day = today()
    warn = day + timedelta(days=conf('REVIEW_WARNING_DAYS'))
    counts = {}

    def remind(obj, recipients, label, due, ct, event, overdue_priority='high'):
        if due is None:
            return 0
        overdue = due < day
        subject = f"{'OVERDUE' if overdue else 'Due soon'}: {label}"
        body = (f"{label}\nDue date: {due:%Y-%m-%d}" +
                ("\n\nThis item is past its due date. Please complete the review and update the record." if overdue
                 else "\n\nPlease schedule the review before the due date."))
        n = 0
        for u in _recipients(*recipients):
            if notify_once(u, subject, body, ct, obj.pk, priority=overdue_priority if overdue else 'normal', template_event=event):
                n += 1
        return n

    n = 0
    for p in Policy.objects.filter(status__in=['approved', 'published'], review_date__lte=warn).select_related('owner', 'department'):
        n += remind(p, [p.owner, _dept_manager(p)], f'Policy review - {p.policy_id} {p.title}', p.review_date, 'governance.policy', 'policy_review')
    counts['policies'] = n

    n = 0
    for p in Procedure.objects.filter(status__in=['approved', 'published'], review_date__lte=warn).select_related('owner', 'department'):
        n += remind(p, [p.owner, _dept_manager(p)], f'Procedure review - {p.procedure_id} {p.title}', p.review_date, 'governance.procedure', 'policy_review')
    counts['procedures'] = n

    n = 0
    risk_warn = day + timedelta(days=conf('RISK_REVIEW_WARNING_DAYS'))
    for r in Risk.objects.exclude(status__in=['closed', 'pending_approval']).filter(review_date__lte=risk_warn).select_related('owner', 'department'):
        n += remind(r, [r.owner, _dept_manager(r)], f'Risk review - {r.risk_id} {r.title}', r.review_date, 'risk.risk', 'risk_assessment')
    counts['risks'] = n

    n = 0
    from bcm.utils import plan_test_status
    for model, label, ct in ((BCPlan, 'BC plan', 'bcm.bcplan'), (DisasterRecoveryPlan, 'DR plan', 'bcm.disasterrecoveryplan')):
        live = model.objects.filter(status__in=['approved', 'active']).select_related('owner')
        for plan in live.filter(review_date__lte=warn):
            n += remind(plan, [plan.owner], f'{label} review - {plan.plan_id} {plan.title}', plan.review_date, ct, 'bcm_test')
        for plan in live:
            ts = plan_test_status(plan)
            if not ts['needs_testing']:
                continue
            last = plan.last_tested_date.strftime('%Y-%m-%d') if plan.last_tested_date else 'never'
            subject = (f"OVERDUE exercise: {plan.plan_id} {plan.title}" if ts['overdue']
                       else f"Exercise due soon: {plan.plan_id} {plan.title}")
            for u in _recipients(plan.owner):
                if notify_once(u, subject,
                               f"{label} '{plan.title}' was last tested: {last}. {ts['recommendation']} "
                               f"(frequency: every {plan.test_frequency_months} months).",
                               ct, plan.pk, priority='high' if ts['overdue'] else 'normal', template_event='bcm_test'):
                    n += 1
    counts['plans'] = n

    n = 0
    bia_cutoff = day - timedelta(days=conf('BIA_REVIEW_INTERVAL_DAYS'))
    for bia in BusinessImpactAnalysis.objects.filter(status__in=['completed', 'approved'], assessment_date__lte=bia_cutoff) \
            .select_related('business_function__owner', 'assessor'):
        fn = bia.business_function
        n += remind(bia, [fn.owner if fn else None, bia.assessor],
                    f'BIA review - {fn.name if fn else "function"}',
                    bia.assessment_date + timedelta(days=conf('BIA_REVIEW_INTERVAL_DAYS')),
                    'bcm.businessimpactanalysis', 'bcm_test')
    counts['bias'] = n

    n = 0
    for ci in ControlImplementation.objects.filter(status__in=['implemented', 'partially_implemented'], next_test_date__lte=warn) \
            .select_related('owner', 'department', 'control'):
        n += remind(ci, [ci.owner, _dept_manager(ci)], f'Control test - {ci.control.control_id} {ci.control.title}',
                    ci.next_test_date, 'compliance.controlimplementation', 'control_testing')
    counts['control_tests'] = n

    n = 0
    soon = day + timedelta(days=conf('UPCOMING_EVENT_DAYS'))
    for a in Audit.objects.filter(status='planned', planned_start_date__range=(day, soon)).select_related('lead_auditor'):
        for u in _recipients(a.lead_auditor, *a.auditors.all()):
            if notify_once(u, f'Audit starting soon: {a.audit_id} {a.title}',
                           f"Audit '{a.title}' is planned to start on {a.planned_start_date:%Y-%m-%d}.",
                           'compliance.audit', a.pk, template_event='audit_scheduled'):
                n += 1
    for t in BCMTest.objects.filter(status='planned', scheduled_date__range=(day, soon)).select_related('coordinator'):
        for u in _recipients(t.coordinator, *t.participants.all()):
            if notify_once(u, f'BCM test scheduled: {t.test_id} {t.title}',
                           f"'{t.title}' ({t.get_test_type_display()}) is scheduled for {t.scheduled_date:%Y-%m-%d}.",
                           'bcm.bcmtest', t.pk, template_event='bcm_test'):
                n += 1
    counts['upcoming_events'] = n
    return counts


# --------------------------------------------------------------------------- #
# 3. Expiry: evidence and risk acceptances
# --------------------------------------------------------------------------- #
def expire_evidence():
    from compliance.models import Evidence

    day = today()
    warn = day + timedelta(days=conf('EVIDENCE_WARNING_DAYS'))
    live = Evidence.objects.filter(status__in=['accepted', 'submitted']).select_related(
        'submitted_by', 'control_implementation__owner', 'control_implementation__control')

    expired_qs = live.filter(valid_until__lt=day)
    for e in expired_qs:
        for u in _recipients(e.submitted_by, e.control_implementation.owner):
            notify_once(u, f'Evidence EXPIRED: {e.evidence_id} {e.title}',
                        f"Evidence for control {e.control_implementation.control.control_id} expired on {e.valid_until:%Y-%m-%d}. "
                        "Please collect and upload current evidence.", 'compliance.evidence', e.pk,
                        priority='high', template_event='evidence_expiring')
    expired = expired_qs.update(status='expired')

    warned = 0
    for e in live.filter(valid_until__range=(day, warn)):
        for u in _recipients(e.submitted_by, e.control_implementation.owner):
            if notify_once(u, f'Evidence expiring soon: {e.evidence_id} {e.title}',
                           f"Evidence for control {e.control_implementation.control.control_id} expires on {e.valid_until:%Y-%m-%d}.",
                           'compliance.evidence', e.pk, template_event='evidence_expiring'):
                warned += 1
    return {'expired': expired, 'warned': warned}


def expire_risk_acceptances():
    from risk.models import RiskAcceptance

    day = today()
    warn = day + timedelta(days=conf('ACCEPTANCE_WARNING_DAYS'))
    approved = RiskAcceptance.objects.filter(status='approved').select_related('risk__owner', 'requested_by', 'approved_by')

    expired_qs = approved.filter(valid_until__lt=day)
    for a in expired_qs:
        for u in _recipients(a.requested_by, a.risk.owner, a.approved_by):
            notify_once(u, f'Risk acceptance EXPIRED: {a.risk.risk_id} {a.risk.title}',
                        f"The acceptance of risk {a.risk.risk_id} expired on {a.valid_until:%Y-%m-%d}. "
                        "The risk must be re-assessed and either treated or re-accepted.",
                        'risk.riskacceptance', a.pk, priority='high', template_event='risk_assessment')
    expired = expired_qs.update(status='expired')

    warned = 0
    for a in approved.filter(valid_until__range=(day, warn)):
        for u in _recipients(a.requested_by, a.risk.owner):
            if notify_once(u, f'Risk acceptance expiring: {a.risk.risk_id} {a.risk.title}',
                           f"The acceptance of risk {a.risk.risk_id} expires on {a.valid_until:%Y-%m-%d}.",
                           'risk.riskacceptance', a.pk, template_event='risk_assessment'):
                warned += 1
    return {'expired': expired, 'warned': warned}


# --------------------------------------------------------------------------- #
# 4. Calculations: residual risk, gap assessments, KPIs
# --------------------------------------------------------------------------- #
def recalculate_residual_risks(organization=None):
    """Recalculate residual risk for every risk whose residual is control-derived."""
    from risk.models import Risk

    qs = Risk.objects.filter(residual_auto=True).exclude(status='closed')
    if organization is not None:
        qs = qs.filter(organization=organization)
    updated = 0
    for risk in qs.prefetch_related('controls'):
        if risk.apply_control_based_residual(save=True):
            updated += 1
    return {'recalculated': updated}


def refresh_gap_assessments():
    """Keep non-approved gap assessments in sync with control implementation status."""
    from compliance.models import GapAssessment
    from compliance.utils import auto_calculate_gap_assessment

    n = 0
    for ga in GapAssessment.objects.exclude(status='approved').select_related('framework', 'organization'):
        try:
            auto_calculate_gap_assessment(ga)
            n += 1
        except Exception:
            logger.exception('Gap assessment %s refresh failed', ga.pk)
    return {'refreshed': n}


KPI_METRICS = {}


def kpi_metric(name):
    def deco(fn):
        KPI_METRICS[name] = fn
        return fn
    return deco


@kpi_metric('compliance_score')
def _kpi_compliance(org):
    from compliance.utils import calculate_compliance_score
    return Decimal(str(calculate_compliance_score(org)['score']))


@kpi_metric('open_high_risks')
def _kpi_high_risks(org):
    from risk.models import Risk
    return Decimal(sum(1 for r in Risk.objects.filter(organization=org).exclude(status='closed')
                       if r.risk_level in ('high', 'critical')))


@kpi_metric('overdue_corrective_actions')
def _kpi_overdue_cars(org):
    from compliance.models import CorrectiveAction
    return Decimal(CorrectiveAction.objects.filter(organization=org, status='overdue').count())


@kpi_metric('open_findings')
def _kpi_open_findings(org):
    from compliance.models import AuditFinding
    return Decimal(AuditFinding.objects.filter(audit__organization=org, status__in=['open', 'in_progress', 'overdue']).count())


@kpi_metric('policies_reviewed_on_time_pct')
def _kpi_policy_reviews(org):
    from governance.models import Policy
    live = Policy.objects.filter(organization=org, status__in=['approved', 'published'], review_date__isnull=False)
    total = live.count()
    if not total:
        return Decimal(100)
    on_time = live.filter(review_date__gte=today()).count()
    return Decimal(round(on_time / total * 100, 2))


@kpi_metric('critical_functions_tested_pct')
def _kpi_functions_tested(org):
    from bcm.models import BusinessFunction
    cutoff = today() - timedelta(days=conf('PLAN_TEST_INTERVAL_DAYS'))
    critical = BusinessFunction.objects.filter(organization=org, criticality__in=['critical', 'essential'], status='active')
    total = critical.count()
    if not total:
        return Decimal(100)
    covered = critical.filter(bc_plans__status__in=['approved', 'active'], bc_plans__last_tested_date__gte=cutoff).distinct().count()
    return Decimal(round(covered / total * 100, 2))


@kpi_metric('evidence_expiring_30d')
def _kpi_evidence_expiring(org):
    from compliance.models import Evidence
    day = today()
    return Decimal(Evidence.objects.filter(organization=org, status__in=['accepted', 'submitted'],
                                           valid_until__range=(day, day + timedelta(days=30))).count())


@kpi_metric('risks_outside_appetite')
def _kpi_outside_appetite(org):
    from risk.models import Risk
    return Decimal(sum(1 for r in Risk.objects.filter(organization=org).exclude(status__in=['closed', 'pending_approval'])
                       if r.appetite_status['status'] != 'within'))


@kpi_metric('kris_red')
def _kpi_kris_red(org):
    from risk.models import KeyRiskIndicator
    return Decimal(KeyRiskIndicator.objects.filter(organization=org, is_active=True, current_status='red').count())


@kpi_metric('critical_functions_recoverable_pct')
def _kpi_recoverable(org):
    from bcm.utils import capability_analysis
    from bcm.models import BusinessFunction
    fns = BusinessFunction.objects.filter(organization=org, status='active', criticality__in=['critical', 'essential'])
    report = capability_analysis(org, fns, test_interval_days=conf('PLAN_TEST_INTERVAL_DAYS'))
    total = report['summary']['total']
    return Decimal(100) if not total else Decimal(round(report['summary']['covered'] / total * 100, 2))


@kpi_metric('overdue_approvals')
def _kpi_overdue_approvals(org):
    from workflow.models import Approval
    return Decimal(Approval.objects.filter(status='pending', due_date__lt=timezone.now(),
                                           workflow_instance__initiated_by__profile__organization=org).count())


def snapshot_kpis():
    """Compute every KPI with a `calculation_config.metric` for every organization (upsert current month)."""
    from core.models import Organization
    from dashboard.models import KPI, KPIValue

    period = today().replace(day=1)
    written = 0
    for kpi in KPI.objects.filter(is_active=True):
        metric = (kpi.calculation_config or {}).get('metric')
        fn = KPI_METRICS.get(metric)
        if not fn:
            continue
        for org in Organization.objects.filter(is_active=True):
            try:
                value = fn(org)
            except Exception:
                logger.exception('KPI %s failed for org %s', kpi.code, org.pk)
                continue
            KPIValue.objects.update_or_create(organization=org, kpi=kpi, period_date=period,
                                              defaults={'value': value, 'breakdown': {'metric': metric}})
            written += 1
    return {'kpi_values': written}


# --------------------------------------------------------------------------- #
# 4b. Risk governance: appetite breaches, KRIs, recovery capability gaps
# --------------------------------------------------------------------------- #
def check_risk_appetite_breaches():
    """
    Flag open risks whose exposure exceeds the applicable appetite: notify the
    owner and department manager, create a treatment task when none is active,
    and escalate risks above tolerance to the next management level.
    """
    from risk.models import Risk
    from workflow.models import Task
    from notifications.models import Escalation

    counts = {'within': 0, 'tolerance': 0, 'breach': 0, 'tasks_created': 0, 'escalations': 0}
    risks = Risk.objects.exclude(status__in=['closed', 'pending_approval']).select_related('owner', 'department', 'category')
    for risk in risks:
        a = risk.appetite_status
        counts[a['status']] += 1
        if a['status'] == 'within':
            continue
        label = 'ABOVE TOLERANCE' if a['status'] == 'breach' else 'Outside appetite'
        body = (f"Risk {risk.risk_id} '{risk.title}' has a {a['basis']} score of {a['score']} against an appetite of "
                f"{a['appetite']} (tolerance {a['tolerance']}). A treatment plan bringing the risk within appetite is required.")
        for u in _recipients(risk.owner, _dept_manager(risk)):
            notify_once(u, f"{label}: {risk.risk_id} {risk.title}", body, 'risk.risk', risk.pk,
                        priority='urgent' if a['status'] == 'breach' else 'high', template_event='risk_assessment')

        has_treatment = risk.treatments.filter(status__in=['planned', 'in_progress']).exists()
        has_task = Task.objects.filter(content_type='risk.risk', object_id=risk.pk, task_type='remediation',
                                       status__in=['pending', 'in_progress', 'overdue']).exists()
        if risk.owner and not has_treatment and not has_task:
            Task.objects.create(
                title=f'Define treatment plan for {risk.risk_id} (outside risk appetite)',
                task_type='remediation', priority='critical' if a['status'] == 'breach' else 'high',
                description=body, assigned_to=risk.owner, content_type='risk.risk', object_id=risk.pk,
                due_date=timezone.now() + timedelta(days=14 if a['status'] == 'breach' else 30),
            )
            counts['tasks_created'] += 1

        if a['status'] == 'breach':
            already = Escalation.objects.filter(content_type='risk.risk', object_id=risk.pk,
                                                status__in=['pending', 'escalated']).exists()
            if not already:
                dept = risk.department
                target = None
                while dept is not None and target is None:
                    if dept.manager_id and dept.manager_id != risk.owner_id:
                        target = dept.manager
                    dept = dept.parent
                Escalation.objects.create(
                    content_type='risk.risk', object_id=risk.pk, object_title=f'{risk.risk_id} {risk.title}'[:500],
                    level=2, escalated_from=risk.owner, escalated_to=target,
                    reason=f"Residual score {a['score']} exceeds risk tolerance {a['tolerance']}", status='pending')
                counts['escalations'] += 1
    return counts


def check_kri_status():
    """Remind KRI owners of overdue measurements and keep red indicators visible."""
    from risk.models import KeyRiskIndicator

    counts = {'measurement_overdue': 0, 'red': 0}
    for kri in KeyRiskIndicator.objects.filter(is_active=True).select_related('owner', 'risk__owner'):
        if kri.is_measurement_overdue:
            counts['measurement_overdue'] += 1
            due = kri.measurement_due_date
            notify_once(kri.owner, f'KRI measurement overdue: {kri.kri_id} {kri.name}',
                        f"Indicator '{kri.name}' is measured {kri.get_frequency_display().lower()}; the last value was recorded "
                        f"{kri.last_measured_at or 'never'}" + (f" (due {due:%Y-%m-%d})." if due else '.'),
                        'risk.keyriskindicator', kri.pk, priority='normal', template_event='risk_assessment')
        if kri.current_status == 'red':
            counts['red'] += 1
            for u in _recipients(kri.owner, kri.risk.owner if kri.risk_id else None):
                notify_once(u, f'KRI RED: {kri.kri_id} {kri.name} = {kri.current_value}{kri.unit}',
                            f"Indicator '{kri.name}' remains above its critical threshold ({kri.critical_threshold}{kri.unit}).",
                            'risk.keyriskindicator', kri.pk, priority='urgent', template_event='risk_assessment')
    return counts


def check_capability_gaps():
    """Run the recovery capability analysis per organization and alert function and DR plan owners to gaps."""
    from django.contrib.auth import get_user_model
    from core.models import Organization
    from bcm.utils import capability_analysis

    User = get_user_model()
    counts = {'functions_checked': 0, 'gaps': 0, 'notified': 0}
    for org in Organization.objects.filter(is_active=True):
        report = capability_analysis(org, test_interval_days=conf('PLAN_TEST_INTERVAL_DAYS'))
        for row in report['functions']:
            counts['functions_checked'] += 1
            if row['status'] == 'covered':
                continue
            if row['function']['criticality'] not in ('critical', 'essential'):
                continue
            counts['gaps'] += 1
            owner_ids = {row['function']['owner_id']}
            for asset in row['assets']:
                for plan in asset['plans']:
                    owner_ids.add(plan['owner_id'])
            owner_ids.discard(None)
            issues = '\n'.join(f'- {i}' for i in row['issues'][:10])
            for u in User.objects.filter(pk__in=owner_ids, is_active=True):
                if notify_once(u, f"Recovery capability gap ({row['status']}): {row['function']['function_id']} {row['function']['name']}",
                               f"Required RTO {row['required']['rto_hours'] if row['required'] else 'n/a'}h. Issues:\n{issues}",
                               'bcm.businessfunction', row['function']['id'], priority='high', template_event='bcm_test'):
                    counts['notified'] += 1
    return counts


# --------------------------------------------------------------------------- #
# 5. Delivery
# --------------------------------------------------------------------------- #
def deliver_notifications(limit=500):
    from notifications.delivery import deliver_pending_notifications
    return deliver_pending_notifications(limit=limit)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
JOBS = OrderedDict([
    ('escalate_overdue_approvals', escalate_overdue_approvals),
    ('remind_upcoming_approvals', remind_upcoming_approvals),
    ('process_escalations', process_escalations),
    ('mark_overdue_items', mark_overdue_items),
    ('send_review_reminders', send_review_reminders),
    ('expire_evidence', expire_evidence),
    ('expire_risk_acceptances', expire_risk_acceptances),
    ('recalculate_residual_risks', recalculate_residual_risks),
    ('refresh_gap_assessments', refresh_gap_assessments),
    ('check_risk_appetite_breaches', check_risk_appetite_breaches),
    ('check_kri_status', check_kri_status),
    ('check_capability_gaps', check_capability_gaps),
    ('snapshot_kpis', snapshot_kpis),
    ('deliver_notifications', deliver_notifications),
])


def run_job(name):
    fn = JOBS[name]
    started = timezone.now()
    try:
        result = fn()
        logger.info('automation %s: %s', name, result)
        return {'job': name, 'ok': True, 'result': result,
                'seconds': round((timezone.now() - started).total_seconds(), 2)}
    except Exception as exc:
        logger.exception('automation %s failed', name)
        return {'job': name, 'ok': False, 'error': str(exc)}


def run_all(only=None):
    names = [n for n in JOBS if not only or n in only]
    return [run_job(n) for n in names]
