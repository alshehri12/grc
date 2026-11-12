# GRC System: Expert Assessment (Risk, BCM, Compliance)

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Scope** | Backend data model, business logic, automation layer, and frontend coverage |
| **Reference standards** | ISO 31000, ISO 22301, ISO/TS 22317, ISO/IEC 27001:2022, NCA ECC, SAMA CSF, PDPL |
| **Question answered** | Does this app fit, and does it automate, risk and BCM work? |

---

## Verdict

**This app is a solid GRC data platform, but it is not yet an automation platform.**

It can replace spreadsheets and document folders for risk, BCM and compliance records, and it has a working author → manager approval flow. It does **not** yet automate the recurring work that consumes a GRC or BCM team's time: reminders, reviews, escalations, recalculations, gap analysis and reporting. Most of the logic for that work has been written, but nothing calls it.

| Area | Fit today | Verdict |
|---|---|---|
| Compliance (NCA ECC, ISO 27001, SAMA, PDPL) | **Good** | Strongest module. Framework → control → implementation → evidence → audit is the right structure. |
| Risk management | **Partial** | The register and heat map are fine. The treatment cycle can't be run from the screens, and scoring is inconsistent. |
| BCM | **Partial** | Holds BIAs, plans and tests, but can't answer the central BCM question: *can we actually recover within our RTOs?* |
| Automation | **Very low** | Only approval routing runs automatically. Everything time-based is unused code. |

---

## 1. Strengths

- **Risk method aligned with ISO 31000.** 5×5 likelihood × impact scoring; inherent, residual and target scores; the four treatment options (mitigate, transfer, accept, avoid); risk acceptance with an expiry date.
- **Sound BIA basics.** RTO, RPO and MTPD, with validation that RTO ≤ MTPD, a check that impact grows over time, and a calculated recommended RTO. Many commercial tools skip these checks.
- **Correct compliance structure.** Frameworks contain domains and controls; controls can be mapped across frameworks; each implementation has a maturity level (0–5). This is the right foundation for meeting several regulators at once.
- **Well-designed workflow engine.** Templates, steps, SLAs, delegation, escalation and approval history.
- **Saudi market fit.** Fully bilingual (Arabic/English) with right-to-left layout; Riyadh time zone; covers NCA, SAMA and PDPL. A real advantage over generic international tools.

---

## 2. Methodology problems

### Risk

**R1. The app uses three different definitions of "critical".**

| Location | Rule for "critical" |
|---|---|
| Risk model and executive dashboard | score ≥ 20 |
| `risk/utils.py` matrix | score ≥ 16 |
| Risk statistics endpoint | likelihood ≥ 4 **and** impact ≥ 4 |

With the demo data, the dashboard reports **2 critical risks** while the risk statistics report **4**. In front of a risk committee or an auditor, this destroys trust in the tool. The organization needs **one** risk matrix, approved by the risk committee and set through configuration, not hard-coded in three places.

**R2. The residual-risk calculation can be badly wrong.**
- It averages only controls that have an effectiveness rating. If one linked control is rated 5/5 and four are not implemented, the result is about 95% effective.
- It treats every control the same. Preventive controls should reduce *likelihood*; detective and corrective controls should reduce *impact*.
- It halves the effect on impact using a fixed rule with no methodological basis.
- It runs only when someone calls the endpoint manually.

**R3. No risk appetite or tolerance.** The appetite threshold is passed as a query parameter. Without board-approved appetite statements per risk category, the app can't automatically flag a risk as outside appetite and escalate it. That flag is the core of ERM governance.

**R4. No key risk indicators (KRIs).** Modern ERM, and SAMA's expectations, rely on indicators with thresholds that warn when a risk is moving. There is no KRI model.

**R5. Approval is confused with assessment.** When a manager approves a risk, its status becomes `assessed`. Confirming a risk is valid is not the same as assessing it, and the register can't tell the two apart.

### BCM

**B1. The core BCM gap analysis is impossible.** *(Most important BCM finding.)* ISO 22301 depends on comparing *the RTO the business needs* with *the RTO IT can deliver*. Today:
- BIA dependencies (systems, staff, vendors) are **free text**, not links to assets.
- DR plans have **no field for achievable RTO or RPO**.
- BCM tests don't record the **RTO actually achieved**; the result is free text.

So the app can't report, for example, "Online Payments needs a 1-hour RTO, but the payment-gateway DR plan achieves 4 hours". Producing that report is the main reason organizations buy BCM software.

**B2. BIA impact uses one score per time point.** ISO/TS 22317 rates impact **separately per category** (financial, operational, legal/regulatory, reputational, customer) at each time point. A single number hides *why* a function is critical.

**B3. BCM and risk aren't connected.**
- There is no BCM risk assessment of threats to critical functions (ISO 22301 §8.2.3).
- Incidents aren't linked to risks, so a real disruption doesn't update the likelihood in the risk register. In mature programs, every incident is evidence that recalibrates the related risk.

**B4. No exercise program.** BC plans have no review or test frequency and no next-test date. A helper (`check_plan_test_status`) exists but is reachable only through one manual endpoint. Annual testing is a regulatory expectation (NCA ECC 3-1, SAMA BCM), so the tool should drive the test schedule.

### Compliance

**C1. Mappings exist, but evidence isn't reused across them.** ECC 2-2 is mapped to ISO A.5.15, but evidence uploaded for one doesn't count toward the other. Without that "test once, comply many" reuse, mapping adds little value.

**C2. "Not applicable" has no justification.** ISO 27001 requires a Statement of Applicability. Marking a control N/A without a written justification will be an audit finding.

**C3. Gap assessments are filled in by hand.** A function to calculate them (`auto_calculate_gap_assessment`) exists, but nothing calls it.

### Governance of the tool itself

**G1. No audit trail.** An `AuditLog` model exists, but the code never writes to it. A GRC system that can't show who changed a risk score or approved a policy would fail its own NCA ECC 2-12 (event logging) check. Auditors will ask for this first.

**G2. No real maker-checker control.**
- Managers' own content is approved automatically, so no second person checks it.
- Through the API, any logged-in user can approve any item or edit users.

For a governance tool, segregation of duties is mandatory.

**G3. Approved documents are hidden.** The visibility rules hide `published` policies and all documents from regular users. Published policies are the main thing employees need to read, and they are exactly what they can't see.

---

## 3. Automation check

| Recurring task | Expected | Today |
|---|---|---|
| Route content for approval | Automatic | ✅ Works. This is the only real automation. |
| Review reminders (policy, risk, BIA, plan) | Automatic | ❌ Celery jobs are written, but no schedule is configured and nothing sends email, so they never run. |
| Escalate a missed SLA to the next manager | Automatic | ❌ Written, never runs. |
| Mark overdue tasks and corrective actions | Automatic | ❌ Written, never runs. |
| Warn before evidence expires | Automatic | ❌ Helper exists; nothing triggers it. |
| Recalculate residual risk when a control changes | Automatic | ❌ Manual endpoint, and the formula is flawed (R2). |
| Flag risks outside appetite | Automatic | ❌ No appetite model (R3). |
| Compare BIA RTO with DR capability | Automatic | ❌ Required data doesn't exist (B1). |
| Remind owners about BC test schedules | Automatic | ❌ No test frequency field (B4). |
| Generate board and committee reports (PDF) | Automatic | ❌ Models and the WeasyPrint library exist; there is no generator or screen. |
| Compliance score and maturity | On demand | ✅ Calculated on request. |

---

## 4. Screen coverage

The database supports far more than users can reach. These records have **no screen**:

- **Risk:** assets, risk assessments, treatment plans, risk acceptances.
- **BCM:** incidents, crisis teams, call trees, test findings.
- **Compliance:** audit findings, corrective actions, gap assessments.

As a result, a risk owner **can't run the treatment cycle** and a BCM manager **can't manage an incident** from the app. These are the core daily tasks of both roles.

---

## 5. Recommended roadmap

### Phase 1: Make it trustworthy (required before production use)
1. Record an audit trail for every create, update, delete and approval (G1).
2. Fix permissions: only the assigned approver can approve, and managers' own content needs a second approver (G2).
3. Use one configurable risk matrix everywhere (R1).
4. Fix visibility of published policies and documents (G3).

### Phase 2: Switch on automation (mostly wiring existing code)
5. Configure the Celery schedule and email delivery so reminders, escalations, overdue checks and evidence-expiry warnings actually run.
6. Recalculate residual risk automatically when a control's status changes, and correct the formula (R2).

### Phase 3: Close the risk and BCM gaps
7. Add risk appetite statements per category and KRIs with thresholds (R3, R4).
8. Build BCM capability analysis: link BIA dependencies to assets, add achievable RTO/RPO to DR plans, record achieved RTO in tests, and report "needed vs. achievable" (B1).
9. Add test frequency and next-test dates to plans, with automatic reminders (B4).
10. Link incidents to risks (B3).

### Phase 4: Complete the user experience
11. Build screens for treatments, incidents, findings and corrective actions, and gap assessments.
12. Add board-ready PDF reports and a Statement of Applicability (C2).

---

## Bottom line

After Phases 1–2, the app is a credible internal tool for compliance and risk registers. To truly **automate** risk and BCM work, comparable to commercial platforms such as Archer, ServiceNow IRM or Fusion, Phase 3 is required, above all the BCM capability analysis (B1).

---

## Implementation status (updated 2026-11-12)

All four phases of the roadmap have been implemented on the `demo-data-and-remote-access` branch. Automated tests: 61.

| # | Roadmap item | Status | Where |
|---|---|---|---|
| 1 | Audit trail for every change and approval (G1) | Done | `core/audit.py`, all viewsets, `/api/core/audit-logs/` |
| 2 | Permissions and maker-checker (G2) | Done | `core/permissions.py`, `workflow/services.py`, `workflow/content.py` |
| 3 | One configurable risk matrix (R1) | Done | `risk/utils.py`, Setting `risk_matrix_thresholds`, `/risk/risks/matrix_config/` |
| 4 | Visibility of published policies and documents (G3) | Done | `governance/views.py` |
| 5 | Automation switched on: reminders, escalations, overdue flags, expiries, e-mail | Done | `core/automation.py`, `manage.py run_automation`, `CELERY_BEAT_SCHEDULE` |
| 6 | Residual risk recalculated from control effectiveness (R2) | Done | `risk/utils.py`, signals, `Risk.residual_auto` |
| 7 | Risk appetite per category and KRIs (R3, R4) | Done | `RiskAppetite`, `KeyRiskIndicator`, `/risk/appetites/`, `/risk/kris/` |
| 8 | BCM capability analysis: BIA needs vs DR capability vs exercise proof (B1, B2) | Done | `bcm/utils.capability_analysis`, `/bcm/functions/capability_analysis/` |
| 9 | Exercise schedule per plan with reminders (B4) | Done | `test_frequency_months`, `next_test_date`, review-reminder job |
| 10 | Incidents linked to risks with automatic re-assessment tasks; function threat profile (B3) | Done | `CrisisIncident.related_risks`, `BusinessFunction.related_risks` |
| 11 | Screens for treatments, acceptances, appetite, KRIs, incidents, capability, findings/CARs, gap assessments | Done | `frontend/src/views/...` (shared `CrudPage.vue`) |
| 12 | Board-ready PDF reports and Statement of Applicability with mandatory N/A justification (C2) | Done | `dashboard/reports.py`, `/dashboard/reports/board-pack/`, `/compliance/implementations/statement_of_applicability/` |
| R5 | Approval is no longer treated as assessment | Done | approved risks return to `identified`; assessment is a separate record |
| C1 | Evidence reuse across mapped controls | **Open** | mappings exist; evidence still counts for one control only |

Remaining recommendations: evidence reuse across framework mappings (C1), per-time-point impact matrix in the BIA (the current model rates impact per category at the MTPD horizon), and a production hardening pass (secret key, `DEBUG`, PostgreSQL, HTTPS) before any internet exposure.
