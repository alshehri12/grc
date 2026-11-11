"""
Seed the database with realistic demo data across all GRC modules.

    python manage.py seed_demo_data            # seed (skips if demo org exists)
    python manage.py seed_demo_data --reset    # wipe previous demo data, then seed

Every demo user gets the password given by --password (default: Demo@12345).
All data is fictional and intended for local demos only.
"""
import io
import random
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone

from core.models import Organization, Department, Role, UserProfile, AuditLog, Setting
from governance.models import (
    PolicyCategory, Policy, PolicyVersion, PolicyAcknowledgment, Procedure, Document,
)
from risk.models import (
    AssetCategory, Asset, RiskCategory, Risk, RiskAssessment, RiskTreatment, RiskAcceptance,
)
from bcm.models import (
    BusinessFunction, BusinessImpactAnalysis, BCPlan, DisasterRecoveryPlan,
    CrisisManagementTeam, CrisisTeamMember, CallTree, CallTreeNode, CrisisIncident,
    BCMTest, BCMTestFinding,
)
from compliance.models import (
    ControlFramework, ControlDomain, Control, ControlImplementation, Audit, AuditFinding,
    CorrectiveAction, Evidence, GapAssessment,
)
from frameworks.models import FrameworkTemplate, ControlMapping, RegulatoryRequirement
from workflow.models import WorkflowInstance, Task
from notifications.models import Notification, Reminder
from dashboard.models import KPI, KPIValue

ORG_CODE = 'DEMO'
DEMO_EMAIL_DOMAIN = 'demo.local'

# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #
DEPARTMENTS = [
    # code, name, name_ar
    ('EXEC', 'Executive Office', 'المكتب التنفيذي'),
    ('IT', 'Information Technology', 'تقنية المعلومات'),
    ('CYBER', 'Cybersecurity', 'الأمن السيبراني'),
    ('RISK', 'Risk Management', 'إدارة المخاطر'),
    ('COMP', 'Compliance & Internal Audit', 'الامتثال والمراجعة الداخلية'),
    ('BCM', 'Business Continuity', 'استمرارية الأعمال'),
    ('OPS', 'Operations', 'العمليات'),
    ('FIN', 'Finance', 'المالية'),
    ('HR', 'Human Resources', 'الموارد البشرية'),
    ('LEGAL', 'Legal Affairs', 'الشؤون القانونية'),
]

USERS = [
    # username, first, last, first_ar, last_ar, dept, role, job, job_ar
    ('khalid.otaibi', 'Khalid', 'Al-Otaibi', 'خالد', 'العتيبي', 'IT', 'manager', 'IT Director', 'مدير تقنية المعلومات'),
    ('majed.ghamdi', 'Majed', 'Al-Ghamdi', 'ماجد', 'الغامدي', 'CYBER', 'manager', 'Chief Information Security Officer', 'رئيس أمن المعلومات'),
    ('sara.qahtani', 'Sara', 'Al-Qahtani', 'سارة', 'القحطاني', 'RISK', 'manager', 'Chief Risk Officer', 'رئيس المخاطر'),
    ('fahad.harbi', 'Fahad', 'Al-Harbi', 'فهد', 'الحربي', 'COMP', 'manager', 'Compliance Manager', 'مدير الامتثال'),
    ('faisal.shahrani', 'Faisal', 'Al-Shahrani', 'فيصل', 'الشهراني', 'BCM', 'manager', 'BCM Manager', 'مدير استمرارية الأعمال'),
    ('noura.zahrani', 'Noura', 'Al-Zahrani', 'نورة', 'الزهراني', 'OPS', 'manager', 'Operations Director', 'مديرة العمليات'),
    ('abdullah.qurashi', 'Abdullah', 'Al-Qurashi', 'عبدالله', 'القرشي', 'FIN', 'manager', 'Chief Financial Officer', 'المدير المالي'),
    ('mona.dosari', 'Mona', 'Al-Dosari', 'منى', 'الدوسري', 'HR', 'manager', 'HR Director', 'مديرة الموارد البشرية'),
    ('nawaf.mutairi', 'Nawaf', 'Al-Mutairi', 'نواف', 'المطيري', 'LEGAL', 'manager', 'General Counsel', 'المستشار القانوني'),
    ('saud.rasheed', 'Saud', 'Al-Rasheed', 'سعود', 'الرشيد', 'EXEC', 'manager', 'Chief Executive Officer', 'الرئيس التنفيذي'),
    ('omar.shammari', 'Omar', 'Al-Shammari', 'عمر', 'الشمري', 'RISK', 'author', 'Senior Risk Analyst', 'محلل مخاطر أول'),
    ('reem.subaie', 'Reem', 'Al-Subaie', 'ريم', 'السبيعي', 'COMP', 'author', 'Compliance Specialist', 'أخصائية امتثال'),
    ('badr.saleh', 'Badr', 'Al-Saleh', 'بدر', 'الصالح', 'COMP', 'author', 'Internal Auditor', 'مراجع داخلي'),
    ('yousef.anazi', 'Yousef', 'Al-Anazi', 'يوسف', 'العنزي', 'IT', 'author', 'Infrastructure Engineer', 'مهندس بنية تحتية'),
    ('lama.malki', 'Lama', 'Al-Malki', 'لمى', 'المالكي', 'CYBER', 'author', 'Security Analyst', 'محللة أمن سيبراني'),
    ('turki.juhani', 'Turki', 'Al-Juhani', 'تركي', 'الجهني', 'BCM', 'author', 'BCM Specialist', 'أخصائي استمرارية أعمال'),
    ('hessa.malik', 'Hessa', 'Al-Malik', 'حصة', 'المالك', 'OPS', 'author', 'Process Analyst', 'محللة عمليات'),
]


def pdf_bytes(title, lines):
    """Render a simple one-page PDF so file fields hold a real, openable document."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _, height = A4
    c.setFont('Helvetica-Bold', 16)
    c.drawString(50, height - 70, title[:80])
    c.setFont('Helvetica-Oblique', 9)
    c.drawString(50, height - 88, 'DEMO DOCUMENT - sample data generated for demonstration purposes only')
    c.setFont('Helvetica', 11)
    y = height - 120
    for line in lines:
        c.drawString(50, y, line[:95])
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


def demo_file(title, filename, lines=None):
    data = pdf_bytes(title, lines or [
        f'Document: {title}',
        'Owner: Demo Organization',
        f'Generated: {timezone.localdate():%Y-%m-%d}',
    ])
    return ContentFile(data, name=filename), len(data)


@contextmanager
def workflow_signals_muted():
    """Disconnect the auto-approval/workflow signals while bulk-loading historical data."""
    import governance.signals as gs
    import risk.signals as rs
    import bcm.signals as bs
    import compliance.signals as cs

    pairs = [
        (gs.trigger_policy_workflow, Policy),
        (gs.trigger_procedure_workflow, Procedure),
        (rs.trigger_risk_workflow, Risk),
        (rs.trigger_risk_acceptance_workflow, RiskAcceptance),
        (bs.trigger_business_function_workflow, BusinessFunction),
        (bs.trigger_bcplan_workflow, BCPlan),
        (bs.trigger_drplan_workflow, DisasterRecoveryPlan),
        (bs.trigger_bcmtest_workflow, BCMTest),
        (cs.trigger_audit_workflow, Audit),
    ]
    for fn, sender in pairs:
        post_save.disconnect(fn, sender=sender)
    try:
        yield
    finally:
        for fn, sender in pairs:
            post_save.connect(fn, sender=sender)


class Command(BaseCommand):
    help = 'Populate the database with realistic demo data for all GRC modules.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo data first.')
        parser.add_argument('--password', default='Demo@12345', help='Password for all demo users.')

    # ------------------------------------------------------------------ #
    def handle(self, *args, **opts):
        self.rng = random.Random(2026)
        self.today = timezone.localdate()
        self.now = timezone.now()
        self.password = opts['password']

        existing = Organization.objects.filter(code=ORG_CODE).first()
        if existing and not opts['reset']:
            self.stdout.write(self.style.WARNING(
                'Demo data already exists. Re-run with --reset to wipe and re-seed.'))
            return
        # Keep the same organization ID across resets so the frontend's saved
        # organization (localStorage) stays valid.
        self.org_id = existing.pk if existing else None

        with transaction.atomic():
            if existing:
                self.reset()
            self.seed_core()
            with workflow_signals_muted():
                self.seed_compliance_library()
                self.seed_governance()
                self.seed_risk()
                self.seed_compliance_ops()
                self.seed_bcm()
                self.seed_frameworks_app()
                self.seed_dashboard()
            self.seed_live_workflows()
            self.seed_tasks_and_notifications()

        self.print_summary()

    # ------------------------------------------------------------------ #
    def d(self, days):
        return self.today + timedelta(days=days)

    def dt(self, days, hours=0):
        return self.now + timedelta(days=days, hours=hours)

    def u(self, username):
        return self.users[username]

    def dept(self, code):
        return self.depts[code]

    # ------------------------------------------------------------------ #
    def reset(self):
        self.stdout.write('Removing previous demo data...')
        demo_users = User.objects.filter(email__endswith=f'@{DEMO_EMAIL_DOMAIN}')
        WorkflowInstance.objects.filter(initiated_by__in=demo_users).delete()
        Task.objects.filter(assigned_to__in=demo_users).delete()
        Notification.objects.filter(recipient__in=demo_users).delete()
        Reminder.objects.filter(recipient__in=demo_users).delete()
        AuditLog.objects.filter(user__in=demo_users).delete()
        Organization.objects.filter(code=ORG_CODE).delete()  # cascades to org-scoped data

        fw_codes = ['NCA-ECC', 'ISO27001', 'SAMA-CSF', 'PDPL']
        Control.objects.filter(domain__framework__code__in=fw_codes).delete()
        ControlFramework.objects.filter(code__in=fw_codes).delete()
        FrameworkTemplate.objects.filter(code__in=fw_codes).delete()
        ControlMapping.objects.filter(source_framework__in=fw_codes).delete()
        RegulatoryRequirement.objects.filter(framework_code__in=fw_codes).delete()
        PolicyCategory.objects.filter(code__startswith='DEMO-').delete()
        AssetCategory.objects.filter(code__startswith='DEMO-').delete()
        RiskCategory.objects.filter(code__startswith='DEMO-').delete()
        KPI.objects.filter(code__startswith='DEMO-').delete()
        demo_users.delete()

    # ------------------------------------------------------------------ #
    # CORE
    # ------------------------------------------------------------------ #
    def seed_core(self):
        self.org = Organization.objects.create(
            id=self.org_id,
            name='Riyadh Digital Services Co.',
            name_ar='شركة الرياض للخدمات الرقمية',
            code=ORG_CODE,
            email=f'info@{DEMO_EMAIL_DOMAIN}',
            phone='+966 11 000 0000',
            address='King Fahd Road, Al Olaya District, Riyadh 12211, Saudi Arabia',
            address_ar='طريق الملك فهد، حي العليا، الرياض 12211، المملكة العربية السعودية',
            commercial_registration='1010000000',
            tax_number='300000000000003',
        )

        self.depts = {}
        for code, name, name_ar in DEPARTMENTS:
            self.depts[code] = Department.objects.create(
                organization=self.org, code=code, name=name, name_ar=name_ar,
                description=f'{name} department', description_ar=f'إدارة {name_ar}',
            )
        for code in ['IT', 'CYBER', 'RISK', 'COMP', 'BCM', 'OPS', 'FIN', 'HR', 'LEGAL']:
            self.depts[code].parent = self.depts['EXEC']
            self.depts[code].save(update_fields=['parent'])

        roles = {r.code: r for r in Role.objects.all()}
        self.users = {}
        for i, (uname, first, last, first_ar, last_ar, dcode, role, job, job_ar) in enumerate(USERS, 1):
            user = User.objects.create_user(
                username=uname, email=f'{uname}@{DEMO_EMAIL_DOMAIN}', password=self.password,
                first_name=first, last_name=last,
            )
            profile = UserProfile.objects.create(
                user=user, organization=self.org, department=self.dept(dcode),
                first_name_ar=first_ar, last_name_ar=last_ar, job_title=job, job_title_ar=job_ar,
                employee_id=f'EMP-{1000 + i}', mobile=f'+966 5{self.rng.randint(0, 9)} {self.rng.randint(100, 999)} {self.rng.randint(1000, 9999)}',
            )
            if role in roles:
                profile.roles.add(roles[role])
            if role == 'manager':
                self.dept(dcode).manager = user
                self.dept(dcode).save(update_fields=['manager'])
            self.users[uname] = user

        # Attach existing superusers to the demo org so the UI has org context.
        for su in User.objects.filter(is_superuser=True):
            profile, _ = UserProfile.objects.get_or_create(user=su)
            if not profile.organization_id:
                profile.organization = self.org
                profile.department = self.dept('IT')
                profile.save()
            if 'admin' in roles:
                profile.roles.add(roles['admin'])

        for key, value, vtype, desc in [
            ('risk_appetite_threshold', '12', 'number', 'Residual risk score above which treatment is mandatory'),
            ('policy_review_months', '12', 'number', 'Default policy review cycle'),
            ('evidence_expiry_warning_days', '30', 'number', 'Days before evidence expiry to warn owners'),
            ('default_language', 'ar', 'string', 'Default UI language'),
        ]:
            Setting.objects.create(organization=self.org, key=key, value=value, value_type=vtype, description=desc)

    # ------------------------------------------------------------------ #
    # COMPLIANCE LIBRARY (frameworks/domains/controls) - needed by other modules
    # ------------------------------------------------------------------ #
    def seed_compliance_library(self):
        library = {
            ('NCA-ECC', 'NCA Essential Cybersecurity Controls', 'الضوابط الأساسية للأمن السيبراني', 'ECC-1:2018',
             'National Cybersecurity Authority', 'الهيئة الوطنية للأمن السيبراني', True): [
                ('1', 'Cybersecurity Governance', 'حوكمة الأمن السيبراني', [
                    ('1-1', 'Cybersecurity Strategy', 'استراتيجية الأمن السيبراني'),
                    ('1-2', 'Cybersecurity Management', 'إدارة الأمن السيبراني'),
                    ('1-3', 'Cybersecurity Policies and Procedures', 'سياسات وإجراءات الأمن السيبراني'),
                    ('1-4', 'Cybersecurity Roles and Responsibilities', 'أدوار ومسؤوليات الأمن السيبراني'),
                    ('1-5', 'Cybersecurity Risk Management', 'إدارة مخاطر الأمن السيبراني'),
                    ('1-9', 'Cybersecurity in Human Resources', 'الأمن السيبراني المتعلق بالموارد البشرية'),
                    ('1-10', 'Cybersecurity Awareness and Training Program', 'برنامج التوعية والتدريب بالأمن السيبراني'),
                ]),
                ('2', 'Cybersecurity Defense', 'تعزيز الأمن السيبراني', [
                    ('2-1', 'Asset Management', 'إدارة الأصول'),
                    ('2-2', 'Identity and Access Management', 'إدارة هويات الدخول والصلاحيات'),
                    ('2-3', 'Information System and Processing Facilities Protection', 'حماية الأنظمة وأجهزة معالجة المعلومات'),
                    ('2-4', 'Email Protection', 'حماية البريد الإلكتروني'),
                    ('2-5', 'Networks Security Management', 'إدارة أمن الشبكات'),
                    ('2-7', 'Data and Information Protection', 'حماية البيانات والمعلومات'),
                    ('2-8', 'Cryptography', 'التشفير'),
                    ('2-9', 'Backup and Recovery Management', 'إدارة النسخ الاحتياطية'),
                    ('2-10', 'Vulnerabilities Management', 'إدارة الثغرات'),
                    ('2-11', 'Penetration Testing', 'اختبار الاختراق'),
                    ('2-12', 'Cybersecurity Event Logs and Monitoring Management', 'إدارة سجلات الأحداث ومراقبة الأمن السيبراني'),
                    ('2-13', 'Cybersecurity Incident and Threat Management', 'إدارة حوادث وتهديدات الأمن السيبراني'),
                    ('2-14', 'Physical Security', 'الأمن المادي'),
                    ('2-15', 'Web Application Security', 'حماية تطبيقات الويب'),
                ]),
                ('3', 'Cybersecurity Resilience', 'صمود الأمن السيبراني', [
                    ('3-1', 'Cybersecurity Resilience Aspects of Business Continuity Management', 'جوانب صمود الأمن السيبراني في إدارة استمرارية الأعمال'),
                ]),
                ('4', 'Third-Party and Cloud Computing Cybersecurity', 'الأمن السيبراني المتعلق بالأطراف الخارجية والحوسبة السحابية', [
                    ('4-1', 'Third-Party Cybersecurity', 'الأمن السيبراني المتعلق بالأطراف الخارجية'),
                    ('4-2', 'Cloud Computing and Hosting Cybersecurity', 'الأمن السيبراني المتعلق بالحوسبة السحابية والاستضافة'),
                ]),
            ],
            ('ISO27001', 'ISO/IEC 27001 Information Security Management', 'المواصفة الدولية ISO/IEC 27001', '2022',
             'International Organization for Standardization', 'المنظمة الدولية للمعايير', False): [
                ('A.5', 'Organizational Controls', 'الضوابط التنظيمية', [
                    ('A.5.1', 'Policies for information security', 'سياسات أمن المعلومات'),
                    ('A.5.2', 'Information security roles and responsibilities', 'أدوار ومسؤوليات أمن المعلومات'),
                    ('A.5.9', 'Inventory of information and other associated assets', 'جرد المعلومات والأصول المرتبطة'),
                    ('A.5.15', 'Access control', 'التحكم في الوصول'),
                    ('A.5.19', 'Information security in supplier relationships', 'أمن المعلومات في العلاقات مع الموردين'),
                    ('A.5.23', 'Information security for use of cloud services', 'أمن المعلومات لاستخدام الخدمات السحابية'),
                    ('A.5.24', 'Incident management planning and preparation', 'التخطيط والاستعداد لإدارة الحوادث'),
                    ('A.5.30', 'ICT readiness for business continuity', 'جاهزية تقنية المعلومات لاستمرارية الأعمال'),
                    ('A.5.34', 'Privacy and protection of PII', 'الخصوصية وحماية البيانات الشخصية'),
                ]),
                ('A.6', 'People Controls', 'ضوابط الأفراد', [
                    ('A.6.1', 'Screening', 'التحقق من الخلفية'),
                    ('A.6.3', 'Information security awareness, education and training', 'التوعية والتدريب في أمن المعلومات'),
                ]),
                ('A.7', 'Physical Controls', 'الضوابط المادية', [
                    ('A.7.1', 'Physical security perimeters', 'محيط الأمن المادي'),
                    ('A.7.4', 'Physical security monitoring', 'مراقبة الأمن المادي'),
                ]),
                ('A.8', 'Technological Controls', 'الضوابط التقنية', [
                    ('A.8.2', 'Privileged access rights', 'صلاحيات الوصول المميزة'),
                    ('A.8.5', 'Secure authentication', 'المصادقة الآمنة'),
                    ('A.8.7', 'Protection against malware', 'الحماية من البرمجيات الخبيثة'),
                    ('A.8.8', 'Management of technical vulnerabilities', 'إدارة الثغرات التقنية'),
                    ('A.8.13', 'Information backup', 'النسخ الاحتياطي للمعلومات'),
                    ('A.8.15', 'Logging', 'تسجيل الأحداث'),
                    ('A.8.16', 'Monitoring activities', 'أنشطة المراقبة'),
                    ('A.8.20', 'Networks security', 'أمن الشبكات'),
                    ('A.8.24', 'Use of cryptography', 'استخدام التشفير'),
                    ('A.8.32', 'Change management', 'إدارة التغيير'),
                ]),
            ],
            ('SAMA-CSF', 'SAMA Cyber Security Framework', 'إطار الأمن السيبراني للبنك المركزي السعودي', '1.0',
             'Saudi Central Bank', 'البنك المركزي السعودي', False): [
                ('3.1', 'Cyber Security Leadership and Governance', 'القيادة والحوكمة', [
                    ('SAMA-3.1.1', 'Cyber Security Governance', 'حوكمة الأمن السيبراني'),
                    ('SAMA-3.1.2', 'Cyber Security Strategy', 'استراتيجية الأمن السيبراني'),
                    ('SAMA-3.1.3', 'Cyber Security Policy', 'سياسة الأمن السيبراني'),
                    ('SAMA-3.1.6', 'Cyber Security Awareness', 'التوعية بالأمن السيبراني'),
                ]),
                ('3.2', 'Cyber Security Risk Management and Compliance', 'إدارة المخاطر والامتثال', [
                    ('SAMA-3.2.1', 'Cyber Security Risk Management', 'إدارة مخاطر الأمن السيبراني'),
                    ('SAMA-3.2.4', 'Cyber Security Audit', 'تدقيق الأمن السيبراني'),
                ]),
                ('3.3', 'Cyber Security Operations and Technology', 'العمليات والتقنية', [
                    ('SAMA-3.3.5', 'Identity and Access Management', 'إدارة الهويات والصلاحيات'),
                    ('SAMA-3.3.14', 'Cyber Security Event Management', 'إدارة أحداث الأمن السيبراني'),
                    ('SAMA-3.3.15', 'Cyber Security Incident Management', 'إدارة حوادث الأمن السيبراني'),
                ]),
                ('3.4', 'Third Party Cyber Security', 'الأمن السيبراني للأطراف الخارجية', [
                    ('SAMA-3.4.2', 'Outsourcing', 'الإسناد الخارجي'),
                    ('SAMA-3.4.3', 'Cloud Computing', 'الحوسبة السحابية'),
                ]),
            ],
            ('PDPL', 'Personal Data Protection Law', 'نظام حماية البيانات الشخصية', '2023',
             'Saudi Data & AI Authority (SDAIA)', 'الهيئة السعودية للبيانات والذكاء الاصطناعي', True): [
                ('PDPL-RIGHTS', 'Data Subject Rights', 'حقوق صاحب البيانات', [
                    ('PDPL-RTS-01', 'Right to be informed and to access personal data', 'الحق في العلم والوصول إلى البيانات'),
                    ('PDPL-RTS-02', 'Right to correction and destruction of personal data', 'الحق في التصحيح والإتلاف'),
                ]),
                ('PDPL-CTRL', 'Controller Obligations', 'التزامات جهة التحكم', [
                    ('PDPL-CTL-01', 'Lawful basis and consent for processing', 'المسوغ النظامي والموافقة على المعالجة'),
                    ('PDPL-CTL-02', 'Privacy notice', 'إشعار الخصوصية'),
                    ('PDPL-CTL-03', 'Records of processing activities', 'سجل أنشطة المعالجة'),
                ]),
                ('PDPL-SEC', 'Security, Breach and Transfer', 'الأمن والتسريب والنقل', [
                    ('PDPL-SEC-01', 'Security of personal data', 'أمن البيانات الشخصية'),
                    ('PDPL-SEC-02', 'Personal data breach notification', 'الإبلاغ عن تسريب البيانات الشخصية'),
                    ('PDPL-SEC-03', 'Transfer of personal data outside the Kingdom', 'نقل البيانات الشخصية خارج المملكة'),
                ]),
            ],
        }

        ctypes = ['preventive', 'preventive', 'detective', 'corrective']
        self.frameworks, self.controls = {}, {}
        for (code, name, name_ar, version, body, body_ar, mandatory), domains in library.items():
            fw = ControlFramework.objects.create(
                code=code, name=name, name_ar=name_ar, version=version,
                issuing_body=body, issuing_body_ar=body_ar, is_mandatory=mandatory,
                description=f'{name} ({version}) issued by {body}.',
                description_ar=f'{name_ar} الصادر عن {body_ar}',
            )
            self.frameworks[code] = fw
            for order, (dcode, dname, dname_ar, controls) in enumerate(domains, 1):
                dom = ControlDomain.objects.create(
                    framework=fw, code=dcode, name=dname, name_ar=dname_ar, order=order,
                    description=f'{dname} domain of {name}.',
                )
                for corder, (cid, title, title_ar) in enumerate(controls, 1):
                    self.controls[cid] = Control.objects.create(
                        domain=dom, control_id=cid, title=title, title_ar=title_ar, order=corder,
                        control_type=self.rng.choice(ctypes),
                        description=f'The organization shall define, implement and maintain requirements for {title.lower()}.',
                        description_ar=f'يجب على الجهة تحديد وتطبيق ومراجعة متطلبات {title_ar}.',
                        implementation_guidance=f'Document the approach for {title.lower()}, assign an owner, and review at least annually.',
                        testing_guidance='Inspect documentation, interview control owner, and sample operating evidence for the review period.',
                        evidence_requirements='Approved policy/procedure, configuration screenshots or reports, and review records.',
                    )

        # Cross-framework mappings (ECC <-> ISO)
        for a, b in [('1-3', 'A.5.1'), ('1-4', 'A.5.2'), ('2-1', 'A.5.9'), ('2-2', 'A.5.15'),
                     ('2-2', 'A.8.2'), ('2-9', 'A.8.13'), ('2-10', 'A.8.8'), ('2-12', 'A.8.15'),
                     ('2-13', 'A.5.24'), ('2-14', 'A.7.1'), ('2-8', 'A.8.24'), ('4-1', 'A.5.19'),
                     ('4-2', 'A.5.23'), ('3-1', 'A.5.30'), ('1-10', 'A.6.3'), ('2-7', 'PDPL-SEC-01')]:
            self.controls[a].mapped_controls.add(self.controls[b])

    # ------------------------------------------------------------------ #
    # GOVERNANCE
    # ------------------------------------------------------------------ #
    def seed_governance(self):
        cats = {}
        for i, (code, name, name_ar) in enumerate([
            ('ISEC', 'Information Security', 'أمن المعلومات'),
            ('DATA', 'Data Governance & Privacy', 'حوكمة البيانات والخصوصية'),
            ('RC', 'Risk & Compliance', 'المخاطر والامتثال'),
            ('BC', 'Business Continuity', 'استمرارية الأعمال'),
            ('HR', 'Human Resources', 'الموارد البشرية'),
            ('OPS', 'Operations', 'العمليات'),
        ], 1):
            cats[code] = PolicyCategory.objects.create(
                code=f'DEMO-{code}', name=name, name_ar=name_ar, order=i,
                description=f'Policies related to {name.lower()}.',
            )

        policies = [
            # id, title, title_ar, cat, dept, owner, status, class, version, months_ago_effective, controls
            ('POL-ISEC-001', 'Information Security Policy', 'سياسة أمن المعلومات', 'ISEC', 'CYBER', 'majed.ghamdi', 'approved', 'internal', '3.1', 10, ['1-3', 'A.5.1']),
            ('POL-ISEC-002', 'Acceptable Use Policy', 'سياسة الاستخدام المقبول', 'ISEC', 'CYBER', 'majed.ghamdi', 'approved', 'internal', '2.0', 14, ['1-9']),
            ('POL-ISEC-003', 'Identity and Access Management Policy', 'سياسة إدارة الهويات والصلاحيات', 'ISEC', 'CYBER', 'majed.ghamdi', 'approved', 'confidential', '2.2', 8, ['2-2', 'A.5.15', 'A.8.2']),
            ('POL-ISEC-004', 'Password and Authentication Standard', 'معيار كلمات المرور والمصادقة', 'ISEC', 'CYBER', 'majed.ghamdi', 'approved', 'internal', '1.4', 6, ['A.8.5']),
            ('POL-ISEC-005', 'Cryptography and Key Management Policy', 'سياسة التشفير وإدارة المفاتيح', 'ISEC', 'CYBER', 'majed.ghamdi', 'pending_review', 'confidential', '1.0', 0, ['2-8', 'A.8.24']),
            ('POL-ISEC-006', 'Cloud Computing Security Policy', 'سياسة أمن الحوسبة السحابية', 'ISEC', 'IT', 'khalid.otaibi', 'approved', 'internal', '1.1', 5, ['4-2', 'A.5.23']),
            ('POL-DATA-001', 'Data Classification and Handling Policy', 'سياسة تصنيف البيانات والتعامل معها', 'DATA', 'COMP', 'fahad.harbi', 'approved', 'internal', '2.0', 12, ['2-7']),
            ('POL-DATA-002', 'Personal Data Protection Policy', 'سياسة حماية البيانات الشخصية', 'DATA', 'LEGAL', 'nawaf.mutairi', 'published', 'public', '1.2', 9, ['PDPL-SEC-01', 'PDPL-CTL-02', 'A.5.34']),
            ('POL-RC-001', 'Enterprise Risk Management Policy', 'سياسة إدارة المخاطر المؤسسية', 'RC', 'RISK', 'sara.qahtani', 'approved', 'internal', '2.1', 11, ['1-5', 'SAMA-3.2.1']),
            ('POL-RC-002', 'Third-Party Risk Management Policy', 'سياسة إدارة مخاطر الأطراف الخارجية', 'RC', 'RISK', 'sara.qahtani', 'approved', 'internal', '1.3', 7, ['4-1', 'A.5.19']),
            ('POL-RC-003', 'Compliance Management Policy', 'سياسة إدارة الامتثال', 'RC', 'COMP', 'fahad.harbi', 'approved', 'internal', '1.0', 4, []),
            ('POL-BC-001', 'Business Continuity Management Policy', 'سياسة إدارة استمرارية الأعمال', 'BC', 'BCM', 'faisal.shahrani', 'approved', 'internal', '2.0', 13, ['3-1', 'A.5.30']),
            ('POL-BC-002', 'Backup and Recovery Policy', 'سياسة النسخ الاحتياطي والاستعادة', 'BC', 'IT', 'khalid.otaibi', 'approved', 'internal', '1.5', 9, ['2-9', 'A.8.13']),
            ('POL-ISEC-007', 'Incident Management Policy', 'سياسة إدارة الحوادث', 'ISEC', 'CYBER', 'majed.ghamdi', 'approved', 'internal', '1.2', 3, ['2-13', 'A.5.24']),
            ('POL-HR-001', 'Remote Work Policy', 'سياسة العمل عن بعد', 'HR', 'HR', 'mona.dosari', 'draft', 'internal', '0.3', 0, []),
            ('POL-HR-002', 'Clean Desk and Clear Screen Policy', 'سياسة المكتب النظيف والشاشة النظيفة', 'HR', 'HR', 'mona.dosari', 'approved', 'internal', '1.0', 16, ['A.7.1']),
            ('POL-OPS-001', 'Change Management Policy', 'سياسة إدارة التغيير', 'OPS', 'IT', 'khalid.otaibi', 'approved', 'internal', '2.3', 15, ['A.8.32']),
            ('POL-ISEC-000', 'Legacy Remote Access Policy', 'سياسة الوصول عن بعد (قديمة)', 'ISEC', 'IT', 'khalid.otaibi', 'retired', 'internal', '1.0', 40, []),
        ]
        self.policies = {}
        for pid, title, title_ar, cat, dcode, owner, status, cls, ver, ago, ctrls in policies:
            eff = self.d(-ago * 30) if ago else None
            approved = status in ('approved', 'published', 'retired')
            p = Policy.objects.create(
                organization=self.org, category=cats[cat], policy_id=pid, title=title, title_ar=title_ar,
                purpose=f'To establish the requirements and responsibilities for {title.lower().replace(" policy", "").replace(" standard", "")} across Riyadh Digital Services Co.',
                purpose_ar=f'تحديد المتطلبات والمسؤوليات المتعلقة بـ{title_ar} في الشركة.',
                scope='Applies to all employees, contractors, and third parties who access company information assets, systems, and facilities.',
                scope_ar='تنطبق على جميع الموظفين والمتعاقدين والأطراف الخارجية الذين يصلون إلى أصول المعلومات والأنظمة والمرافق.',
                policy_statement=(
                    f'1. The company shall maintain controls for {title.lower()} aligned with NCA ECC and ISO/IEC 27001.\n'
                    '2. Department managers are accountable for compliance within their areas.\n'
                    '3. Exceptions must be documented, risk-assessed, and approved by the policy owner.\n'
                    '4. Violations may result in disciplinary action in line with HR regulations.\n'
                    '5. This policy shall be reviewed at least annually or upon significant change.'
                ),
                policy_statement_ar='١. تلتزم الشركة بتطبيق الضوابط اللازمة.\n٢. مدراء الإدارات مسؤولون عن الالتزام.\n٣. يجب توثيق الاستثناءات واعتمادها.',
                version=ver, status=status, classification=cls, owner=self.u(owner), department=self.dept(dcode),
                effective_date=eff, review_date=(eff + timedelta(days=365)) if eff else None,
                approved_by=self.u('saud.rasheed') if approved else None,
                approved_date=(eff - timedelta(days=7)) if (approved and eff) else None,
                created_by=self.u(owner),
            )
            for c in ctrls:
                p.related_controls.add(self.controls[c])
            self.policies[pid] = p
            if approved and ver != '1.0':
                PolicyVersion.objects.create(
                    policy=p, version=ver, title=title, title_ar=title_ar, purpose=p.purpose,
                    scope=p.scope, policy_statement=p.policy_statement, created_by=self.u(owner),
                    change_summary='Annual review: aligned with latest regulatory updates and clarified roles.',
                    change_summary_ar='المراجعة السنوية: المواءمة مع التحديثات التنظيمية وتوضيح الأدوار.',
                )

        # Acknowledgments of core policies
        for pid in ['POL-ISEC-001', 'POL-ISEC-002', 'POL-DATA-002', 'POL-HR-002']:
            p = self.policies[pid]
            for user in self.rng.sample(list(self.users.values()), 11):
                PolicyAcknowledgment.objects.create(policy=p, user=user, version=p.version, ip_address='10.10.1.25')

        procedures = [
            ('PRC-IAM-001', 'User Access Provisioning and De-provisioning', 'إجراء منح وإلغاء صلاحيات المستخدمين', 'POL-ISEC-003', 'IT', 'khalid.otaibi', 'approved',
             ['Line manager submits access request via the IT service portal.', 'Asset/system owner approves the requested access level.', 'IT provisions the account within 2 business days and records the ticket.', 'HR notifies IT of leavers; access is revoked on the last working day.']),
            ('PRC-IAM-002', 'Quarterly User Access Review', 'إجراء المراجعة الربعية لصلاحيات المستخدمين', 'POL-ISEC-003', 'CYBER', 'majed.ghamdi', 'approved',
             ['Cybersecurity extracts user lists from critical systems.', 'System owners review and confirm or revoke each entitlement.', 'IT removes revoked access within 5 business days.', 'Results are retained as audit evidence.']),
            ('PRC-INC-001', 'Cybersecurity Incident Response', 'إجراء الاستجابة لحوادث الأمن السيبراني', 'POL-ISEC-007', 'CYBER', 'majed.ghamdi', 'approved',
             ['Detect and log the event in the SIEM / ticketing system.', 'Triage severity using the incident classification matrix.', 'Contain, eradicate and recover affected systems.', 'Notify NCA within the required timeline for critical incidents.', 'Conduct post-incident review and record lessons learned.']),
            ('PRC-BKP-001', 'Backup Verification and Restore Testing', 'إجراء التحقق من النسخ الاحتياطي واختبار الاستعادة', 'POL-BC-002', 'IT', 'khalid.otaibi', 'approved',
             ['Monitor daily backup job status reports.', 'Perform monthly sample restore for each critical system.', 'Record restore time and compare against RTO.', 'Escalate failures to the IT Director within 24 hours.']),
            ('PRC-VUL-001', 'Vulnerability Management', 'إجراء إدارة الثغرات', 'POL-ISEC-001', 'CYBER', 'majed.ghamdi', 'approved',
             ['Run authenticated vulnerability scans monthly.', 'Prioritize findings by CVSS and asset criticality.', 'Patch critical vulnerabilities within 14 days, high within 30 days.', 'Track exceptions in the risk register.']),
            ('PRC-CHG-001', 'IT Change Management', 'إجراء إدارة التغيير التقني', 'POL-OPS-001', 'IT', 'khalid.otaibi', 'approved',
             ['Raise a change request with impact and rollback plan.', 'Change Advisory Board reviews normal changes weekly.', 'Implement in approved window and validate.', 'Close the change with post-implementation review.']),
            ('PRC-PDP-001', 'Personal Data Breach Notification', 'إجراء الإبلاغ عن تسريب البيانات الشخصية', 'POL-DATA-002', 'LEGAL', 'nawaf.mutairi', 'approved',
             ['Assess whether personal data is affected.', 'Notify the competent authority within 72 hours of becoming aware.', 'Notify affected data subjects where the breach may cause harm.', 'Document the breach and remediation in the breach register.']),
            ('PRC-BCM-001', 'Business Continuity Plan Activation', 'إجراء تفعيل خطة استمرارية الأعمال', 'POL-BC-001', 'BCM', 'faisal.shahrani', 'approved',
             ['Incident commander assesses disruption against activation criteria.', 'Crisis Management Team is convened via the call tree.', 'Critical functions relocate to the alternate site.', 'Status updates are issued every 4 hours until stand-down.']),
            ('PRC-TPR-001', 'Vendor Security Due Diligence', 'إجراء العناية الواجبة الأمنية للموردين', 'POL-RC-002', 'RISK', 'sara.qahtani', 'pending_review',
             ['Vendor completes the security questionnaire.', 'Risk team rates vendor inherent risk.', 'Contract includes cybersecurity and data protection clauses.', 'High-risk vendors are reassessed annually.']),
        ]
        for pid, title, title_ar, pol, dcode, owner, status, steps in procedures:
            Procedure.objects.create(
                organization=self.org, policy=self.policies[pol], procedure_id=pid, title=title, title_ar=title_ar,
                purpose=f'Define the operational steps for {title.lower()}.',
                purpose_ar=f'تحديد الخطوات التشغيلية لـ{title_ar}.',
                scope='All in-scope systems and personnel of Riyadh Digital Services Co.',
                scope_ar='جميع الأنظمة والموظفين ضمن النطاق.',
                procedure_steps='\n'.join(f'{i}. {s}' for i, s in enumerate(steps, 1)),
                version='1.0' if status != 'approved' else self.rng.choice(['1.0', '1.1', '1.2', '2.0']),
                status=status, owner=self.u(owner), department=self.dept(dcode),
                effective_date=self.d(-self.rng.randint(30, 300)) if status == 'approved' else None,
                review_date=self.d(self.rng.randint(20, 300)), created_by=self.u(owner),
            )

        documents = [
            ('DOC-STD-001', 'Secure Configuration Baseline - Windows Server', 'معيار الإعدادات الآمنة - ويندوز سيرفر', 'standard', 'IT', 'yousef.anazi', 'active', 'confidential'),
            ('DOC-STD-002', 'Network Segmentation Standard', 'معيار تقسيم الشبكات', 'standard', 'CYBER', 'lama.malki', 'active', 'confidential'),
            ('DOC-GDL-001', 'Secure Software Development Guideline', 'دليل التطوير الآمن للبرمجيات', 'guideline', 'IT', 'khalid.otaibi', 'active', 'internal'),
            ('DOC-GDL-002', 'Phishing Awareness Guide for Employees', 'دليل التوعية بالتصيد الاحتيالي', 'guideline', 'CYBER', 'lama.malki', 'active', 'public'),
            ('DOC-FRM-001', 'Access Request Form', 'نموذج طلب صلاحية', 'form', 'IT', 'yousef.anazi', 'active', 'internal'),
            ('DOC-FRM-002', 'Risk Acceptance Form', 'نموذج قبول المخاطر', 'form', 'RISK', 'omar.shammari', 'active', 'internal'),
            ('DOC-TPL-001', 'Business Impact Analysis Template', 'قالب تحليل أثر الأعمال', 'template', 'BCM', 'turki.juhani', 'active', 'internal'),
            ('DOC-TPL-002', 'Vendor Security Questionnaire', 'استبيان أمن الموردين', 'template', 'RISK', 'omar.shammari', 'under_review', 'internal'),
            ('DOC-REC-001', 'Records of Processing Activities (ROPA)', 'سجل أنشطة معالجة البيانات', 'record', 'LEGAL', 'nawaf.mutairi', 'active', 'restricted'),
            ('DOC-REC-002', 'Board Risk Committee Minutes - Q3', 'محضر لجنة المخاطر - الربع الثالث', 'record', 'RISK', 'sara.qahtani', 'active', 'restricted'),
            ('DOC-STD-000', 'Legacy VPN Configuration Standard', 'معيار إعدادات الشبكة الخاصة (قديم)', 'standard', 'IT', 'yousef.anazi', 'archived', 'internal'),
        ]
        for did, title, title_ar, dtype, dcode, owner, status, cls in documents:
            f, size = demo_file(title, f'{did.lower()}.pdf')
            Document.objects.create(
                organization=self.org, document_id=did, title=title, title_ar=title_ar, document_type=dtype,
                description=f'{title} maintained by the {self.dept(dcode).name} department.',
                version=self.rng.choice(['1.0', '1.1', '2.0']), status=status, classification=cls,
                file=f, file_size=size, file_type='application/pdf', owner=self.u(owner),
                department=self.dept(dcode), effective_date=self.d(-self.rng.randint(30, 400)),
                review_date=self.d(self.rng.randint(15, 365)), is_public=(cls == 'public'),
                created_by=self.u(owner),
            )

    # ------------------------------------------------------------------ #
    # RISK
    # ------------------------------------------------------------------ #
    def seed_risk(self):
        acats = {}
        for code, name, name_ar in [
            ('APP', 'Business Applications', 'تطبيقات الأعمال'), ('INF', 'Infrastructure', 'البنية التحتية'),
            ('DATA', 'Information / Data', 'المعلومات والبيانات'), ('FAC', 'Facilities', 'المرافق'),
            ('SEC', 'Security Tools', 'أدوات الأمن'), ('END', 'End-user Devices', 'أجهزة المستخدمين'),
        ]:
            acats[code] = AssetCategory.objects.create(code=f'DEMO-{code}', name=name, name_ar=name_ar)

        assets = [
            ('AST-001', 'ERP System (Finance & HR)', 'نظام تخطيط الموارد', 'APP', 'critical', 'abdullah.qurashi', 'yousef.anazi', 'FIN', (4, 5, 4), 'Primary DC - Riyadh'),
            ('AST-002', 'Customer Self-Service Portal', 'بوابة الخدمة الذاتية للعملاء', 'APP', 'critical', 'noura.zahrani', 'yousef.anazi', 'OPS', (4, 4, 5), 'Cloud (KSA region)'),
            ('AST-003', 'Mobile Application (iOS/Android)', 'تطبيق الجوال', 'APP', 'high', 'noura.zahrani', 'yousef.anazi', 'OPS', (4, 4, 4), 'Cloud (KSA region)'),
            ('AST-004', 'Customer Database (PostgreSQL)', 'قاعدة بيانات العملاء', 'DATA', 'critical', 'khalid.otaibi', 'yousef.anazi', 'IT', (5, 5, 4), 'Primary DC - Riyadh'),
            ('AST-005', 'Active Directory / Identity Platform', 'نظام إدارة الهويات', 'INF', 'critical', 'khalid.otaibi', 'yousef.anazi', 'IT', (4, 5, 5), 'Primary DC - Riyadh'),
            ('AST-006', 'Email & Collaboration Suite', 'البريد الإلكتروني ومنصة التعاون', 'APP', 'high', 'khalid.otaibi', 'yousef.anazi', 'IT', (4, 3, 4), 'SaaS'),
            ('AST-007', 'Primary Data Center', 'مركز البيانات الرئيسي', 'FAC', 'critical', 'khalid.otaibi', 'yousef.anazi', 'IT', (3, 4, 5), 'Riyadh - Olaya'),
            ('AST-008', 'Disaster Recovery Site', 'موقع التعافي من الكوارث', 'FAC', 'high', 'faisal.shahrani', 'yousef.anazi', 'BCM', (3, 4, 4), 'Jeddah'),
            ('AST-009', 'Perimeter Firewall Cluster', 'مجموعة جدران الحماية', 'SEC', 'critical', 'majed.ghamdi', 'lama.malki', 'CYBER', (3, 5, 5), 'Primary DC - Riyadh'),
            ('AST-010', 'SIEM Platform', 'منصة إدارة الأحداث الأمنية', 'SEC', 'high', 'majed.ghamdi', 'lama.malki', 'CYBER', (4, 4, 3), 'Primary DC - Riyadh'),
            ('AST-011', 'Backup Appliance & Tape Library', 'نظام النسخ الاحتياطي', 'INF', 'high', 'khalid.otaibi', 'yousef.anazi', 'IT', (4, 5, 4), 'Primary DC - Riyadh'),
            ('AST-012', 'Payment Gateway Integration', 'تكامل بوابة الدفع', 'APP', 'critical', 'abdullah.qurashi', 'yousef.anazi', 'FIN', (5, 5, 5), 'Third-party hosted'),
            ('AST-013', 'Employee Laptops', 'أجهزة الموظفين المحمولة', 'END', 'medium', 'khalid.otaibi', 'yousef.anazi', 'IT', (3, 3, 3), 'All offices'),
            ('AST-014', 'Document Management System', 'نظام إدارة الوثائق', 'APP', 'medium', 'fahad.harbi', 'yousef.anazi', 'COMP', (4, 4, 3), 'Primary DC - Riyadh'),
            ('AST-015', 'HR Employee Records', 'سجلات الموظفين', 'DATA', 'high', 'mona.dosari', 'yousef.anazi', 'HR', (5, 4, 3), 'ERP System'),
            ('AST-016', 'Contact Center Telephony (IP-PBX)', 'نظام الاتصال لمركز خدمة العملاء', 'INF', 'high', 'noura.zahrani', 'yousef.anazi', 'OPS', (2, 3, 5), 'Primary DC - Riyadh'),
        ]
        self.assets = {}
        for aid, name, name_ar, cat, crit, owner, cust, dcode, (c, i, a), loc in assets:
            self.assets[aid] = Asset.objects.create(
                organization=self.org, category=acats[cat], asset_id=aid, name=name, name_ar=name_ar,
                description=f'{name} supporting company operations.', criticality=crit, owner=self.u(owner),
                custodian=self.u(cust), department=self.dept(dcode), confidentiality_value=c,
                integrity_value=i, availability_value=a, location=loc, created_by=self.u(cust),
            )

        rcats = {}
        for code, name, name_ar, color in [
            ('CYB', 'Cybersecurity', 'الأمن السيبراني', '#dc3545'), ('OPR', 'Operational', 'تشغيلية', '#fd7e14'),
            ('CMP', 'Compliance & Regulatory', 'الامتثال والتنظيم', '#6f42c1'), ('FIN', 'Financial', 'مالية', '#198754'),
            ('STR', 'Strategic', 'استراتيجية', '#0d6efd'), ('TPR', 'Third-Party', 'الأطراف الخارجية', '#20c997'),
            ('REP', 'Reputational', 'السمعة', '#ffc107'),
        ]:
            rcats[code] = RiskCategory.objects.create(code=f'DEMO-{code}', name=name, name_ar=name_ar, color=color)

        Y = self.today.year
        risks = [
            # id, title, title_ar, type, cat, dept, owner, (iL,iI), (rL,rI), (tL,tI), status, assets, controls, desc
            ('R-001', 'Ransomware attack encrypting critical servers', 'هجوم فدية يشفر الخوادم الحرجة', 'cyber', 'CYB', 'CYBER', 'majed.ghamdi', (4, 5), (3, 5), (2, 4), 'treating', ['AST-004', 'AST-005', 'AST-011'], ['2-3', '2-9', 'A.8.7'],
             'Threat actors could exploit unpatched systems or phishing to deploy ransomware, encrypting production servers and backups.'),
            ('R-002', 'Phishing leading to credential compromise', 'التصيد الاحتيالي المؤدي لاختراق بيانات الدخول', 'cyber', 'CYB', 'CYBER', 'majed.ghamdi', (5, 4), (3, 3), (2, 3), 'monitoring', ['AST-006', 'AST-005'], ['2-4', '1-10', 'A.8.5'],
             'Employees may disclose credentials through targeted phishing emails, enabling unauthorized access to email and internal systems.'),
            ('R-003', 'Excessive privileged access not reviewed', 'صلاحيات مميزة مفرطة دون مراجعة', 'cyber', 'CYB', 'CYBER', 'lama.malki', (4, 4), (3, 4), (2, 3), 'treating', ['AST-005', 'AST-004'], ['2-2', 'A.8.2'],
             'Administrative accounts accumulate over time without periodic review, increasing insider and lateral movement risk.'),
            ('R-004', 'Unpatched internet-facing vulnerabilities', 'ثغرات غير مرقعة في الأنظمة المكشوفة على الإنترنت', 'cyber', 'CYB', 'CYBER', 'lama.malki', (4, 4), (2, 4), (2, 3), 'monitoring', ['AST-002', 'AST-009'], ['2-10', '2-15', 'A.8.8'],
             'Delays in patching public-facing applications may allow exploitation of known CVEs.'),
            ('R-005', 'Personal data breach of customer records', 'تسريب البيانات الشخصية للعملاء', 'compliance', 'CMP', 'LEGAL', 'nawaf.mutairi', (3, 5), (2, 5), (1, 4), 'treating', ['AST-004', 'AST-002'], ['2-7', 'PDPL-SEC-01', 'PDPL-SEC-02'],
             'Unauthorized disclosure of customer PII could trigger PDPL penalties, mandatory notification and reputational damage.'),
            ('R-006', 'Non-compliance with NCA ECC requirements', 'عدم الامتثال لمتطلبات الضوابط الأساسية للأمن السيبراني', 'compliance', 'CMP', 'COMP', 'fahad.harbi', (3, 4), (2, 4), (1, 3), 'treating', [], ['1-2', '1-3'],
             'Gaps in mandatory ECC controls identified during self-assessment may lead to regulatory findings.'),
            ('R-007', 'Primary data center power or cooling failure', 'انقطاع الطاقة أو التبريد في مركز البيانات الرئيسي', 'operational', 'OPR', 'IT', 'khalid.otaibi', (2, 5), (2, 4), (1, 4), 'monitoring', ['AST-007'], ['2-14', '3-1'],
             'Prolonged utility outage exceeding UPS/generator capacity could halt all hosted services.'),
            ('R-008', 'Payment gateway provider outage', 'انقطاع مزود بوابة الدفع', 'operational', 'TPR', 'FIN', 'abdullah.qurashi', (3, 5), (3, 4), (2, 3), 'assessed', ['AST-012'], ['4-1'],
             'Single payment provider dependency; outage would prevent customers from completing transactions.'),
            ('R-009', 'Key person dependency in IT operations', 'الاعتماد على أشخاص محددين في عمليات تقنية المعلومات', 'operational', 'OPR', 'IT', 'khalid.otaibi', (3, 3), (3, 3), (2, 2), 'assessed', [], ['1-9'],
             'Critical infrastructure knowledge is concentrated in two engineers without documented runbooks.'),
            ('R-010', 'Cloud misconfiguration exposing storage', 'إعدادات سحابية خاطئة تكشف وحدات التخزين', 'cyber', 'CYB', 'IT', 'khalid.otaibi', (3, 4), (2, 3), (1, 3), 'monitoring', ['AST-002', 'AST-003'], ['4-2', 'A.5.23'],
             'Misconfigured cloud storage buckets or security groups could expose data publicly.'),
            ('R-011', 'Inadequate vendor security due diligence', 'قصور في العناية الواجبة الأمنية للموردين', 'operational', 'TPR', 'RISK', 'sara.qahtani', (3, 3), (3, 3), (2, 2), 'treating', [], ['4-1', 'A.5.19'],
             'Third parties with system access are onboarded without consistent security assessments.'),
            ('R-012', 'Foreign exchange volatility on vendor contracts', 'تقلب أسعار الصرف على عقود الموردين', 'financial', 'FIN', 'FIN', 'abdullah.qurashi', (3, 2), (2, 2), (2, 2), 'monitoring', [], [],
             'USD-denominated licensing costs may increase with currency fluctuations.'),
            ('R-013', 'Fraudulent payment transactions', 'عمليات دفع احتيالية', 'financial', 'FIN', 'FIN', 'abdullah.qurashi', (3, 4), (2, 3), (2, 2), 'monitoring', ['AST-012'], [],
             'Card-not-present fraud and account takeover may cause chargebacks and losses.'),
            ('R-014', 'Delay in digital transformation roadmap', 'تأخر خارطة طريق التحول الرقمي', 'strategic', 'STR', 'EXEC', 'saud.rasheed', (3, 3), (3, 3), (2, 2), 'assessed', [], [],
             'Resource constraints may delay strategic initiatives aligned with Vision 2030 digital goals.'),
            ('R-015', 'Negative social media exposure after service outage', 'التغطية السلبية في وسائل التواصل بعد انقطاع الخدمة', 'reputational', 'REP', 'OPS', 'noura.zahrani', (3, 3), (2, 3), (2, 2), 'monitoring', ['AST-002'], [],
             'Extended outages may trigger public complaints and erode customer trust.'),
            ('R-016', 'Insufficient security logging and monitoring', 'قصور في تسجيل ومراقبة الأحداث الأمنية', 'cyber', 'CYB', 'CYBER', 'majed.ghamdi', (3, 4), (3, 3), (2, 2), 'treating', ['AST-010'], ['2-12', 'A.8.15', 'A.8.16'],
             'Not all critical systems forward logs to the SIEM, limiting detection capability.'),
            ('R-017', 'Backup restoration failure', 'فشل استعادة النسخ الاحتياطية', 'operational', 'OPR', 'IT', 'khalid.otaibi', (2, 5), (2, 4), (1, 3), 'monitoring', ['AST-011'], ['2-9', 'A.8.13'],
             'Backups may not be restorable within RTO due to untested procedures or media failure.'),
            ('R-018', 'Loss or theft of unencrypted laptops', 'فقدان أو سرقة أجهزة محمولة غير مشفرة', 'cyber', 'CYB', 'IT', 'yousef.anazi', (3, 3), (1, 3), (1, 2), 'closed', ['AST-013'], ['2-8', 'A.8.24'],
             'Lost devices could expose sensitive data. Mitigated by full-disk encryption rollout.'),
            ('R-019', 'Regulatory change: new data localization rules', 'تغير تنظيمي: متطلبات توطين البيانات', 'compliance', 'CMP', 'LEGAL', 'nawaf.mutairi', (2, 4), (2, 3), (1, 3), 'identified', [], ['PDPL-SEC-03'],
             'Evolving data transfer rules may require relocating some SaaS workloads to in-Kingdom regions.'),
            ('R-020', 'Insider data exfiltration', 'تسريب البيانات من قبل موظف داخلي', 'cyber', 'CYB', 'CYBER', 'lama.malki', (2, 4), (2, 4), (1, 3), 'identified', ['AST-004', 'AST-015'], ['2-7'],
             'A disgruntled employee could exfiltrate sensitive data via removable media or personal cloud storage.'),
        ]
        self.risks = {}
        for (rid, title, title_ar, rtype, cat, dcode, owner, inh, res, tgt, status, assets, ctrls, desc) in risks:
            r = Risk.objects.create(
                organization=self.org, category=rcats[cat], risk_id=f'RSK-{Y}-{rid[2:]}', title=title, title_ar=title_ar,
                description=desc, risk_type=rtype, status=status,
                risk_source='Risk workshop / threat intelligence / internal audit',
                owner=self.u(owner), department=self.dept(dcode),
                inherent_likelihood=inh[0], inherent_impact=inh[1],
                residual_likelihood=res[0] if status != 'identified' else None,
                residual_impact=res[1] if status != 'identified' else None,
                # Risks with linked controls get their residual from control effectiveness
                # (recalculated by automation); the rest carry a manual residual assessment.
                residual_auto=bool(ctrls),
                target_likelihood=tgt[0], target_impact=tgt[1],
                identified_date=self.d(-self.rng.randint(30, 360)),
                review_date=self.d(self.rng.randint(-20, 120)), created_by=self.u(owner),
            )
            for a in assets:
                r.assets.add(self.assets[a])
            for c in ctrls:
                r.controls.add(self.controls[c])
            self.risks[rid] = r

        # Assessments
        for rid, r in self.risks.items():
            if r.status == 'identified':
                continue
            RiskAssessment.objects.create(
                risk=r, assessment_type='initial', status='approved',
                assessment_date=r.identified_date + timedelta(days=7),
                likelihood_score=r.inherent_likelihood, impact_score=r.inherent_impact,
                likelihood_rationale='Based on threat landscape, historical incidents, and existing control gaps.',
                impact_rationale='Considering financial, operational, regulatory and reputational consequences.',
                control_effectiveness=0, findings='Initial inherent assessment completed in risk workshop.',
                recommendations='Define treatment plan and assign owner.',
                assessor=self.u('omar.shammari'), approved_by=self.u('sara.qahtani'),
                approved_date=r.identified_date + timedelta(days=10),
            )
            if r.residual_likelihood:
                eff = int(100 - (r.residual_likelihood * r.residual_impact) / (r.inherent_likelihood * r.inherent_impact) * 100)
                done = self.rng.random() > 0.25
                RiskAssessment.objects.create(
                    risk=r, assessment_type='periodic', status='completed' if done else 'in_progress',
                    assessment_date=self.d(-self.rng.randint(5, 60)),
                    likelihood_score=r.residual_likelihood, impact_score=r.residual_impact,
                    likelihood_rationale='Reduced due to implemented preventive controls.',
                    impact_rationale='Impact partially reduced by detective and recovery controls.',
                    control_effectiveness=max(0, min(100, eff)),
                    findings='Controls operating as designed for sampled period.' if done else '',
                    recommendations='Continue monitoring; re-assess in next quarter.',
                    assessor=self.u('omar.shammari'),
                )

        treatments = [
            ('R-001', 'mitigate', 'Deploy EDR on all servers and endpoints', 'نشر حلول الكشف والاستجابة على جميع الأجهزة', 'in_progress', 65, 450000, 'majed.ghamdi'),
            ('R-001', 'mitigate', 'Implement immutable offline backups', 'تطبيق نسخ احتياطية غير قابلة للتعديل', 'in_progress', 40, 280000, 'khalid.otaibi'),
            ('R-002', 'mitigate', 'Quarterly phishing simulation program', 'برنامج محاكاة التصيد الربعي', 'completed', 100, 60000, 'lama.malki'),
            ('R-002', 'mitigate', 'Enforce MFA for all remote and email access', 'فرض المصادقة متعددة العوامل', 'completed', 100, 90000, 'khalid.otaibi'),
            ('R-003', 'mitigate', 'Deploy Privileged Access Management (PAM) solution', 'تطبيق حل إدارة الصلاحيات المميزة', 'in_progress', 30, 520000, 'majed.ghamdi'),
            ('R-004', 'mitigate', 'Monthly vulnerability scanning and 14-day patch SLA', 'فحص شهري للثغرات واتفاقية ترقيع خلال 14 يوماً', 'completed', 100, 75000, 'lama.malki'),
            ('R-005', 'mitigate', 'Data Loss Prevention (DLP) for email and endpoints', 'تطبيق حل منع تسرب البيانات', 'planned', 0, 380000, 'majed.ghamdi'),
            ('R-005', 'transfer', 'Procure cyber insurance covering data breach costs', 'شراء تأمين سيبراني يغطي تكاليف التسريب', 'in_progress', 50, 150000, 'abdullah.qurashi'),
            ('R-006', 'mitigate', 'ECC remediation program (12 open gaps)', 'برنامج معالجة فجوات الضوابط الأساسية', 'in_progress', 55, 200000, 'fahad.harbi'),
            ('R-007', 'mitigate', 'Upgrade UPS capacity and add second generator', 'رفع سعة أنظمة الطاقة غير المنقطعة', 'planned', 0, 900000, 'khalid.otaibi'),
            ('R-008', 'mitigate', 'Onboard secondary payment gateway provider', 'إضافة مزود بوابة دفع احتياطي', 'planned', 10, 120000, 'abdullah.qurashi'),
            ('R-009', 'mitigate', 'Document runbooks and cross-train staff', 'توثيق أدلة التشغيل وتدريب الموظفين', 'in_progress', 45, 20000, 'khalid.otaibi'),
            ('R-011', 'mitigate', 'Implement vendor risk assessment workflow', 'تطبيق سير عمل تقييم مخاطر الموردين', 'in_progress', 60, 50000, 'sara.qahtani'),
            ('R-012', 'accept', 'Accept FX risk within budget tolerance', 'قبول مخاطر أسعار الصرف ضمن حدود الميزانية', 'completed', 100, 0, 'abdullah.qurashi'),
            ('R-016', 'mitigate', 'Onboard remaining critical systems to SIEM', 'ربط الأنظمة الحرجة المتبقية بمنصة المراقبة', 'in_progress', 70, 110000, 'lama.malki'),
            ('R-018', 'mitigate', 'Full-disk encryption on all laptops', 'تشفير كامل للأقراص على جميع الأجهزة المحمولة', 'completed', 100, 35000, 'yousef.anazi'),
            ('R-014', 'mitigate', 'Establish PMO with quarterly steering reviews', 'إنشاء مكتب إدارة مشاريع مع مراجعات ربعية', 'deferred', 15, 300000, 'saud.rasheed'),
        ]
        for rid, opt, title, title_ar, status, pct, cost, owner in treatments:
            r = self.risks[rid]
            start = self.d(-self.rng.randint(60, 200))
            RiskTreatment.objects.create(
                risk=r, treatment_option=opt, title=title, title_ar=title_ar,
                description=f'{title} to reduce the likelihood and/or impact of "{r.title}".',
                status=status, progress_percentage=pct, estimated_cost=Decimal(cost),
                expected_residual_likelihood=r.target_likelihood, expected_residual_impact=r.target_impact,
                owner=self.u(owner), start_date=start,
                due_date=start + timedelta(days=self.rng.randint(90, 270)),
                completed_date=self.d(-self.rng.randint(5, 50)) if status == 'completed' else None,
                progress_notes='On track.' if status == 'in_progress' else '', created_by=self.u(owner),
            )

        RiskAcceptance.objects.create(
            risk=self.risks['R-012'], justification='Cost of hedging exceeds expected FX loss; exposure is within approved budget tolerance of 5%.',
            accepted_likelihood=2, accepted_impact=2, status='approved', valid_from=self.d(-120), valid_until=self.d(245),
            requested_by=self.u('abdullah.qurashi'), requested_date=self.d(-125), approved_by=self.u('saud.rasheed'),
            approved_date=self.d(-120), approval_comments='Approved by Risk Committee. Review at year end.',
        )
        RiskAcceptance.objects.create(
            risk=self.risks['R-009'], justification='Temporary acceptance until runbooks are completed and a third engineer is hired.',
            conditions='Weekly knowledge-transfer sessions; on-call rotation documented.',
            accepted_likelihood=3, accepted_impact=3, status='expired', valid_from=self.d(-300), valid_until=self.d(-30),
            requested_by=self.u('khalid.otaibi'), requested_date=self.d(-305), approved_by=self.u('sara.qahtani'),
            approved_date=self.d(-300),
        )

    # ------------------------------------------------------------------ #
    # COMPLIANCE OPERATIONS
    # ------------------------------------------------------------------ #
    def seed_compliance_ops(self):
        owners_by_prefix = {
            '1-': ('fahad.harbi', 'COMP'), '2-': ('majed.ghamdi', 'CYBER'), '3-': ('faisal.shahrani', 'BCM'),
            '4-': ('sara.qahtani', 'RISK'), 'A.5': ('fahad.harbi', 'COMP'), 'A.6': ('mona.dosari', 'HR'),
            'A.7': ('khalid.otaibi', 'IT'), 'A.8': ('majed.ghamdi', 'CYBER'), 'SAMA': ('fahad.harbi', 'COMP'),
            'PDPL': ('nawaf.mutairi', 'LEGAL'),
        }
        weights = [
            ('implemented', 45), ('partially_implemented', 25), ('in_progress', 12),
            ('planned', 8), ('not_implemented', 7), ('not_applicable', 3),
        ]
        statuses = [s for s, w in weights for _ in range(w)]
        maturity = {'implemented': (3, 5), 'partially_implemented': (2, 3), 'in_progress': (1, 2),
                    'planned': (0, 1), 'not_implemented': (0, 0), 'not_applicable': (0, 0)}

        self.impls = {}
        for cid, ctrl in self.controls.items():
            owner, dcode = next(v for k, v in owners_by_prefix.items() if cid.startswith(k))
            st = self.rng.choice(statuses)
            if ctrl.domain.framework.code == 'SAMA-CSF' and st == 'implemented' and self.rng.random() < 0.5:
                st = 'partially_implemented'
            lo, hi = maturity[st]
            gap = st in ('partially_implemented', 'in_progress', 'planned', 'not_implemented')
            self.impls[cid] = ControlImplementation.objects.create(
                organization=self.org, control=ctrl, status=st, maturity_level=self.rng.randint(lo, hi),
                implementation_details=(f'{ctrl.title} is implemented through documented procedures and technical controls.'
                                        if st != 'not_applicable' else 'Not applicable to current business scope.'),
                owner=self.u(owner), department=self.dept(dcode),
                last_tested_date=self.d(-self.rng.randint(20, 300)) if st in ('implemented', 'partially_implemented') else None,
                next_test_date=self.d(self.rng.randint(10, 200)),
                effectiveness_rating=self.rng.randint(3, 5) if st == 'implemented' else (self.rng.randint(2, 3) if st == 'partially_implemented' else None),
                gap_description=f'Control not fully operating for all in-scope systems ({ctrl.control_id}).' if gap else '',
                remediation_plan='Complete rollout, document procedure and collect operating evidence.' if gap else '',
                target_date=self.d(self.rng.randint(30, 180)) if gap else None,
            )

        # Evidence for implemented controls
        ev_types = ['document', 'screenshot', 'report', 'configuration', 'log']
        ev_n = 0
        for cid, impl in self.impls.items():
            if impl.status not in ('implemented', 'partially_implemented') or self.rng.random() < 0.35:
                continue
            ev_n += 1
            etype = self.rng.choice(ev_types)
            title = f'{impl.control.title} - {etype.title()} Evidence'
            f, size = demo_file(title, f'evd-{ev_n:03d}.pdf', [
                f'Control: {impl.control.control_id} {impl.control.title}',
                f'Framework: {impl.control.domain.framework.name}',
                f'Evidence type: {etype}', 'Reviewed and validated by compliance team.',
            ])
            collected = self.d(-self.rng.randint(10, 340))
            valid_until = collected + timedelta(days=365)
            status = 'expired' if valid_until < self.today else self.rng.choice(['accepted', 'accepted', 'accepted', 'submitted', 'rejected'])
            Evidence.objects.create(
                organization=self.org, control_implementation=impl, evidence_id=f'EVD-{ev_n:03d}', title=title[:250],
                evidence_type=etype, status=status, description=f'Evidence supporting operation of {impl.control.control_id}.',
                file=f, file_size=size, collection_date=collected, valid_from=collected, valid_until=valid_until,
                submitted_by=impl.owner, submitted_date=collected + timedelta(days=2),
                reviewed_by=self.u('fahad.harbi') if status in ('accepted', 'rejected', 'expired') else None,
                reviewed_date=collected + timedelta(days=5) if status in ('accepted', 'rejected', 'expired') else None,
                review_notes='Insufficient - screenshot does not show date/time.' if status == 'rejected' else '',
            )

        Y = self.today.year
        audits = [
            ('AUD-%d-01' % Y, 'ISO 27001 Surveillance Audit', 'تدقيق المراقبة لشهادة ISO 27001', 'surveillance', 'completed', 'Gulf Assurance Partners (demo)', -150, -146, ['ISO27001'], ['IT', 'CYBER', 'HR']),
            ('AUD-%d-02' % Y, 'NCA ECC Compliance Assessment', 'تقييم الامتثال للضوابط الأساسية للأمن السيبراني', 'regulatory', 'fieldwork', '', -20, 15, ['NCA-ECC'], ['CYBER', 'IT', 'COMP']),
            ('AUD-%d-03' % Y, 'Internal Audit - Identity & Access Management', 'مراجعة داخلية - إدارة الهويات والصلاحيات', 'internal', 'completed', '', -95, -80, ['NCA-ECC', 'ISO27001'], ['IT', 'CYBER']),
            ('AUD-%d-04' % Y, 'Internal Audit - Backup & Disaster Recovery', 'مراجعة داخلية - النسخ الاحتياطي والتعافي', 'internal', 'reporting', '', -40, -25, ['NCA-ECC'], ['IT', 'BCM']),
            ('AUD-%d-05' % Y, 'PDPL Readiness Review', 'مراجعة الجاهزية لنظام حماية البيانات الشخصية', 'internal', 'planned', '', 25, 45, ['PDPL'], ['LEGAL', 'IT', 'OPS']),
            ('AUD-%d-06' % Y, 'SAMA CSF Maturity Assessment', 'تقييم النضج وفق إطار SAMA', 'external', 'planned', 'Riyadh Cyber Advisory (demo)', 70, 90, ['SAMA-CSF'], ['CYBER', 'RISK']),
            ('AUD-%d-07' % (Y - 1), 'Internal Audit - Third-Party Management', 'مراجعة داخلية - إدارة الأطراف الخارجية', 'internal', 'completed', '', -300, -285, ['NCA-ECC'], ['RISK', 'FIN']),
        ]
        self.audits = {}
        for aid, title, title_ar, atype, status, firm, s, e, fws, depts in audits:
            started = status not in ('planned', 'draft')
            done = status == 'completed'
            a = Audit.objects.create(
                organization=self.org, audit_id=aid, title=title, title_ar=title_ar, audit_type=atype, status=status,
                scope=f'Assessment of controls under {", ".join(fws)} for departments: {", ".join(depts)}.',
                objectives='Evaluate design and operating effectiveness of in-scope controls and identify non-conformities.',
                lead_auditor=self.u('badr.saleh') if not firm else self.u('fahad.harbi'), external_firm=firm,
                planned_start_date=self.d(s), planned_end_date=self.d(e),
                actual_start_date=self.d(s) if started else None, actual_end_date=self.d(e) if done else None,
                audit_criteria=', '.join(self.frameworks[f].name for f in fws),
                methodology='Document review, interviews, walkthroughs, and sample-based testing.',
                report_date=self.d(e + 10) if done else None,
                executive_summary='Overall control environment is adequate with improvement areas noted in findings.' if done else '',
                conclusion='Satisfactory with minor non-conformities.' if done else '',
                created_by=self.u('fahad.harbi'),
            )
            for f in fws:
                a.frameworks.add(self.frameworks[f])
            for d in depts:
                a.departments.add(self.dept(d))
            a.auditors.add(self.u('badr.saleh'), self.u('reem.subaie'))
            for impl in list(self.impls.values()):
                if impl.control.domain.framework.code in fws and self.rng.random() < 0.4:
                    a.controls.add(impl.control)
            self.audits[aid] = a

        findings = [
            # audit idx, title, type, status, control, dept, assignee, due offset
            (0, 'Supplier security reviews not performed annually', 'minor_nc', 'closed', 'A.5.19', 'RISK', 'sara.qahtani', -60),
            (0, 'Awareness training completion below 90% target', 'minor_nc', 'closed', 'A.6.3', 'HR', 'mona.dosari', -45),
            (0, 'Good practice: mature change management process', 'positive', 'closed', 'A.8.32', 'IT', 'khalid.otaibi', None),
            (0, 'Log retention period not formally defined', 'observation', 'closed', 'A.8.15', 'CYBER', 'majed.ghamdi', -30),
            (2, 'Leaver accounts remain active beyond last working day', 'major_nc', 'in_progress', '2-2', 'IT', 'khalid.otaibi', 20),
            (2, 'Privileged accounts lack quarterly access review', 'major_nc', 'overdue', 'A.8.2', 'CYBER', 'majed.ghamdi', -10),
            (2, 'Shared generic admin accounts on network devices', 'minor_nc', 'pending_verification', '2-2', 'IT', 'yousef.anazi', 5),
            (2, 'MFA not enforced on VPN for contractors', 'minor_nc', 'closed', 'A.8.5', 'IT', 'khalid.otaibi', -20),
            (3, 'Restore tests not performed for ERP system', 'major_nc', 'open', '2-9', 'IT', 'khalid.otaibi', 30),
            (3, 'DR site network capacity insufficient for full failover', 'minor_nc', 'open', '3-1', 'BCM', 'faisal.shahrani', 60),
            (3, 'Backup encryption keys stored on same server', 'observation', 'open', '2-8', 'CYBER', 'lama.malki', 45),
            (1, 'Cybersecurity strategy not approved by board', 'minor_nc', 'open', '1-1', 'CYBER', 'majed.ghamdi', 40),
            (1, 'Web application firewall in detection-only mode', 'observation', 'open', '2-15', 'CYBER', 'lama.malki', 30),
            (6, 'Vendor contracts lack right-to-audit clauses', 'minor_nc', 'closed', '4-1', 'LEGAL', 'nawaf.mutairi', -200),
            (6, 'No inventory of third parties with data access', 'major_nc', 'closed', '4-1', 'RISK', 'sara.qahtani', -180),
        ]
        audit_list = list(self.audits.values())
        fcount, car_n = {}, 0
        for idx, title, ftype, status, cid, dcode, assignee, due in findings:
            audit = audit_list[idx]
            fcount[idx] = fcount.get(idx, 0) + 1
            closed = status == 'closed'
            f = AuditFinding.objects.create(
                audit=audit, finding_id=f'{audit.audit_id}-F{fcount[idx]:02d}', title=title, finding_type=ftype, status=status,
                description=f'During testing, auditors observed: {title.lower()}.',
                criteria_reference=f'{self.controls[cid].domain.framework.code} {cid}', control=self.controls[cid],
                evidence_collected='Sample of 25 records reviewed; system configuration exported.',
                risk_rating={'major_nc': 'High', 'minor_nc': 'Medium', 'observation': 'Low', 'positive': 'N/A'}.get(ftype, 'Medium'),
                recommendation='Define clear ownership, implement the control consistently, and retain evidence.' if ftype != 'positive' else '',
                assigned_to=self.u(assignee), department=self.dept(dcode),
                due_date=self.d(due) if due is not None else None,
                management_response='Agreed. Remediation plan in place.' if ftype != 'positive' else '',
                response_date=self.d(-5) if ftype != 'positive' else None,
                closure_evidence='Verification evidence reviewed and accepted.' if closed else '',
                closed_by=self.u('fahad.harbi') if closed else None, closed_date=self.d((due or 0) - 3) if closed else None,
            )
            if ftype in ('major_nc', 'minor_nc'):
                car_n += 1
                car_status = {'closed': 'closed', 'in_progress': 'in_progress', 'overdue': 'overdue',
                              'pending_verification': 'pending_verification'}.get(status, 'open')
                CorrectiveAction.objects.create(
                    organization=self.org, finding=f, car_id=f'CAR-{Y}-{car_n:03d}', title=f'Remediate: {title}'[:300],
                    status=car_status, priority='high' if ftype == 'major_nc' else 'medium',
                    root_cause='Process not formally defined and no automated control to enforce it.',
                    action_description='Document procedure, implement technical enforcement, and perform monthly checks.',
                    owner=self.u(assignee), target_date=self.d(due or 30),
                    completed_date=self.d((due or 0) - 5) if car_status in ('closed', 'pending_verification') else None,
                    verification_method='Re-test a sample of 25 items after implementation.',
                    verified_by=self.u('badr.saleh') if car_status == 'closed' else None,
                    verified_date=self.d((due or 0) - 3) if car_status == 'closed' else None,
                    is_effective=True if car_status == 'closed' else None, created_by=self.u('badr.saleh'),
                )

        # Gap assessments computed from implementation status
        for fw_code, title, title_ar, status, days in [
            ('NCA-ECC', 'NCA ECC Annual Self-Assessment', 'التقييم الذاتي السنوي للضوابط الأساسية', 'approved', -60),
            ('PDPL', 'PDPL Gap Assessment', 'تقييم الفجوات لنظام حماية البيانات', 'in_progress', -10),
            ('ISO27001', 'ISO 27001:2022 Transition Gap Analysis', 'تحليل فجوات الانتقال إلى ISO 27001:2022', 'completed', -200),
        ]:
            impls = [i for i in self.impls.values() if i.control.domain.framework.code == fw_code]
            cnt = lambda s: sum(1 for i in impls if i.status == s)
            total, impl_n, part, na = len(impls), cnt('implemented'), cnt('partially_implemented'), cnt('not_applicable')
            applicable = max(total - na, 1)
            GapAssessment.objects.create(
                organization=self.org, framework=self.frameworks[fw_code], assessment_id=f'GAP-{Y}-{fw_code}',
                title=title, title_ar=title_ar, status=status, assessment_date=self.d(days),
                scope='All in-scope systems, processes and departments.', total_controls=total,
                implemented_controls=impl_n, partially_implemented=part, not_implemented=total - impl_n - part - na,
                not_applicable=na, compliance_score=Decimal(round((impl_n + 0.5 * part) / applicable * 100, 2)),
                maturity_score=Decimal(round(sum(i.maturity_level for i in impls) / max(total, 1), 2)),
                executive_summary=f'The organization has achieved partial compliance with {self.frameworks[fw_code].name}.',
                key_gaps='Privileged access reviews; backup restore testing; formal approval of strategy documents.',
                recommendations='Prioritize remediation of mandatory controls and establish continuous compliance monitoring.',
                assessor=self.u('reem.subaie'),
                approved_by=self.u('fahad.harbi') if status == 'approved' else None,
                approved_date=self.d(days + 10) if status == 'approved' else None,
            )

    # ------------------------------------------------------------------ #
    # BCM
    # ------------------------------------------------------------------ #
    def seed_bcm(self):
        functions = [
            ('BF-001', 'Data Center Operations', 'عمليات مركز البيانات', 'IT', 'khalid.otaibi', 'critical', ['AST-007', 'AST-005', 'AST-009']),
            ('BF-002', 'Online Payments Processing', 'معالجة المدفوعات الإلكترونية', 'FIN', 'abdullah.qurashi', 'critical', ['AST-012', 'AST-004']),
            ('BF-003', 'Customer Portal & Mobile Services', 'خدمات بوابة العملاء والتطبيق', 'OPS', 'noura.zahrani', 'critical', ['AST-002', 'AST-003', 'AST-004']),
            ('BF-004', 'Customer Contact Center', 'مركز اتصال العملاء', 'OPS', 'noura.zahrani', 'essential', ['AST-016', 'AST-002']),
            ('BF-005', 'Cybersecurity Monitoring (SOC)', 'مراقبة الأمن السيبراني', 'CYBER', 'majed.ghamdi', 'essential', ['AST-010', 'AST-009']),
            ('BF-006', 'Payroll Processing', 'معالجة الرواتب', 'HR', 'mona.dosari', 'essential', ['AST-001', 'AST-015']),
            ('BF-007', 'Financial Reporting & Treasury', 'التقارير المالية والخزينة', 'FIN', 'abdullah.qurashi', 'essential', ['AST-001']),
            ('BF-008', 'IT Service Desk', 'مكتب خدمة تقنية المعلومات', 'IT', 'khalid.otaibi', 'necessary', ['AST-006', 'AST-005']),
            ('BF-009', 'Procurement & Vendor Management', 'المشتريات وإدارة الموردين', 'FIN', 'abdullah.qurashi', 'necessary', ['AST-001']),
            ('BF-010', 'Regulatory Reporting', 'التقارير التنظيمية', 'COMP', 'fahad.harbi', 'necessary', ['AST-014']),
            ('BF-011', 'Recruitment & Onboarding', 'التوظيف والتهيئة', 'HR', 'mona.dosari', 'desirable', ['AST-001']),
        ]
        self.functions = {}
        for fid, name, name_ar, dcode, owner, crit, assets in functions:
            bf = BusinessFunction.objects.create(
                organization=self.org, department=self.dept(dcode), function_id=fid, name=name, name_ar=name_ar,
                description=f'{name} - delivers key services that support company operations and customers.',
                description_ar=f'{name_ar} - تقدم خدمات رئيسية تدعم عمليات الشركة والعملاء.',
                criticality=crit, status='active', owner=self.u(owner), created_by=self.u(owner),
            )
            for a in assets:
                bf.related_assets.add(self.assets[a])
            self.functions[fid] = bf
        F = self.functions
        for fid, deps in {'BF-002': ['BF-001'], 'BF-003': ['BF-001', 'BF-002'], 'BF-004': ['BF-003', 'BF-008'],
                          'BF-005': ['BF-001'], 'BF-006': ['BF-007'], 'BF-008': ['BF-001'], 'BF-010': ['BF-007']}.items():
            for dep in deps:
                F[fid].dependent_functions.add(F[dep])

        bia = [
            # fid, rto, rpo, mtpd, impacts(1,4,8,24,72), daily loss, min staff, status
            ('BF-001', 2, 0, 8, (3, 4, 5, 5, 5), 1200000, 4, 'approved'),
            ('BF-002', 1, 0, 4, (4, 5, 5, 5, 5), 2500000, 3, 'approved'),
            ('BF-003', 4, 1, 12, (2, 3, 4, 5, 5), 900000, 5, 'approved'),
            ('BF-004', 4, 4, 24, (2, 3, 3, 4, 5), 250000, 12, 'approved'),
            ('BF-005', 4, 1, 24, (2, 3, 3, 4, 5), 150000, 3, 'completed'),
            ('BF-006', 72, 24, 120, (1, 1, 1, 2, 4), 80000, 2, 'approved'),
            ('BF-007', 24, 24, 72, (1, 1, 2, 3, 4), 120000, 3, 'completed'),
            ('BF-008', 8, 4, 48, (1, 2, 2, 3, 4), 40000, 3, 'in_progress'),
            ('BF-009', 72, 24, 168, (1, 1, 1, 2, 3), 30000, 2, 'draft'),
            ('BF-010', 48, 24, 120, (1, 1, 1, 2, 4), 60000, 1, 'completed'),
        ]
        for fid, rto, rpo, mtpd, imp, loss, staff, status in bia:
            bf = F[fid]
            obj = BusinessImpactAnalysis(
                organization=self.org, business_function=bf, assessment_date=self.d(-self.rng.randint(30, 200)),
                status=status, rto_hours=rto, rpo_hours=rpo, mtpd_hours=mtpd,
                impact_1_hour=imp[0], impact_4_hours=imp[1], impact_8_hours=imp[2], impact_24_hours=imp[3], impact_72_hours=imp[4],
                financial_impact_daily=Decimal(loss),
                operational_impact=f'Disruption to {bf.name.lower()} would halt dependent services and create backlogs.',
                reputational_impact='Customer complaints and negative media/social coverage after prolonged outage.',
                regulatory_impact='Potential breach of service availability obligations and regulatory reporting deadlines.',
                staff_dependencies=f'Minimum {staff} trained staff including function lead and backup.',
                system_dependencies=', '.join(a.name for a in bf.related_assets.all()),
                vendor_dependencies='Cloud hosting provider; telecom carrier; payment processor (where applicable).',
                minimum_staff=staff, minimum_equipment='Laptops with VPN access, softphones, access to DR environment.',
                peak_periods='Month-end, Ramadan and Eid seasons, salary disbursement days (25th-27th).',
                assessor=self.u('turki.juhani'),
                approved_by=self.u('faisal.shahrani') if status == 'approved' else None,
                approved_date=self.d(-20) if status == 'approved' else None,
            )
            obj.full_clean(exclude=['organization'])
            obj.save()

        self.bcplans = {}
        for pid, title, title_ar, status, funcs, owner, tested in [
            ('BCP-001', 'Corporate Business Continuity Plan', 'خطة استمرارية الأعمال المؤسسية', 'active', ['BF-002', 'BF-003', 'BF-004', 'BF-006', 'BF-007'], 'faisal.shahrani', -90),
            ('BCP-002', 'IT Services Continuity Plan', 'خطة استمرارية خدمات تقنية المعلومات', 'approved', ['BF-001', 'BF-005', 'BF-008'], 'khalid.otaibi', -150),
            ('BCP-003', 'Pandemic & Workforce Unavailability Plan', 'خطة الجوائح وعدم توفر القوى العاملة', 'under_revision', ['BF-004', 'BF-006', 'BF-011'], 'mona.dosari', -400),
            ('BCP-004', 'Finance Function Continuity Plan', 'خطة استمرارية الإدارة المالية', 'draft', ['BF-007', 'BF-009'], 'abdullah.qurashi', None),
        ]:
            p = BCPlan.objects.create(
                organization=self.org, plan_id=pid, title=title, title_ar=title_ar, status=status,
                version='2.1' if status == 'active' else '1.0',
                scope='Covers critical business functions, people, premises, technology and suppliers listed in the plan.',
                objectives='Resume critical functions within approved RTOs and protect staff, customers and reputation.',
                activation_criteria='Loss of primary site > 4 hours; loss of critical system beyond RTO; >30% staff unavailable.',
                recovery_strategies='Relocate to alternate site; activate work-from-home; fail over to DR data center; manual workarounds.',
                roles_responsibilities='Incident Commander: BCM Manager. Deputy: IT Director. Communications: Operations Director.',
                communication_plan='Call tree activation within 30 minutes; SMS broadcast to staff; customer notice via portal and social media.',
                resource_requirements='50 workstations at alternate site; 200 VPN licenses; satellite phone for leadership.',
                alternate_site='Jeddah regional office (3rd floor) and DR data center.',
                owner=self.u(owner), effective_date=self.d(-200) if status in ('active', 'approved') else None,
                review_date=self.d(self.rng.randint(30, 200)),
                last_tested_date=self.d(tested) if tested else None,
                approved_by=self.u('saud.rasheed') if status in ('active', 'approved') else None,
                approved_date=self.d(-205) if status in ('active', 'approved') else None, created_by=self.u(owner),
            )
            for fid in funcs:
                p.covered_functions.add(F[fid])
            self.bcplans[pid] = p

        self.drplans = {}
        for pid, title, title_ar, bcp, status, systems, freq, tested in [
            ('DRP-001', 'Primary Data Center Failover Plan', 'خطة التحويل لمركز البيانات الاحتياطي', 'BCP-002', 'active', 'ERP, Customer Database, Active Directory, Firewalls, SIEM', 'Daily full + 15-min log shipping', -120),
            ('DRP-002', 'Customer Portal & Mobile Backend DR', 'خطة التعافي لبوابة العملاء والتطبيق', 'BCP-002', 'approved', 'Customer Portal, Mobile API, CDN configuration', 'Continuous replication (multi-zone)', -60),
            ('DRP-003', 'ERP System Recovery Plan', 'خطة استعادة نظام تخطيط الموارد', 'BCP-001', 'approved', 'ERP application & database servers', 'Nightly full, hourly incremental', -200),
            ('DRP-004', 'Email & Collaboration Recovery', 'خطة استعادة البريد الإلكتروني', 'BCP-002', 'draft', 'Email, Teams, SharePoint', 'Vendor-managed (SaaS)', None),
        ]:
            self.drplans[pid] = DisasterRecoveryPlan.objects.create(
                organization=self.org, bc_plan=self.bcplans[bcp], plan_id=pid, title=title, title_ar=title_ar,
                status=status, scope=f'Technical recovery of: {systems}.', covered_systems=systems,
                recovery_procedures='1. Declare disaster\n2. Promote DR database replicas\n3. Switch DNS / load balancer\n4. Validate application health\n5. Notify business owners',
                backup_strategy='3-2-1 strategy with immutable copy and offsite replication.',
                backup_location='DR data center - Jeddah', backup_frequency=freq,
                dr_site_location='Tier III DR data center, Jeddah', vendor_contacts='Hosting NOC: +966 12 000 0000',
                owner=self.u('khalid.otaibi'), effective_date=self.d(-180) if status != 'draft' else None,
                review_date=self.d(self.rng.randint(30, 180)), last_tested_date=self.d(tested) if tested else None,
                approved_by=self.u('khalid.otaibi') if status != 'draft' else None, created_by=self.u('yousef.anazi'),
            )

        # Crisis teams
        cmt = CrisisManagementTeam.objects.create(organization=self.org, name='Crisis Management Team', name_ar='فريق إدارة الأزمات')
        irt = CrisisManagementTeam.objects.create(organization=self.org, name='Cyber Incident Response Team', name_ar='فريق الاستجابة للحوادث السيبرانية')
        for team, members in [
            (cmt, [('saud.rasheed', 'commander'), ('faisal.shahrani', 'deputy'), ('noura.zahrani', 'operations'),
                   ('nawaf.mutairi', 'communications'), ('khalid.otaibi', 'it'), ('abdullah.qurashi', 'finance'), ('mona.dosari', 'hr')]),
            (irt, [('majed.ghamdi', 'commander'), ('lama.malki', 'deputy'), ('yousef.anazi', 'it'), ('nawaf.mutairi', 'communications')]),
        ]:
            for uname, role in members:
                CrisisTeamMember.objects.create(
                    team=team, user=self.u(uname), role=role, primary_phone=self.u(uname).profile.mobile,
                    role_description=f'{role.title()} role during crisis response.',
                )

        tree = CallTree.objects.create(
            organization=self.org, name='Executive Emergency Call Tree', name_ar='شجرة الاتصال الطارئة للإدارة العليا',
            description='Cascade used to notify leadership and department heads during a major disruption.',
            root_caller=self.u('faisal.shahrani'), last_tested=self.dt(-45),
        )
        root = CallTreeNode.objects.create(call_tree=tree, user=self.u('faisal.shahrani'), order=1, phone=self.u('faisal.shahrani').profile.mobile)
        for i, (mgr, reports) in enumerate([
            ('saud.rasheed', []), ('khalid.otaibi', ['yousef.anazi']), ('majed.ghamdi', ['lama.malki']),
            ('noura.zahrani', ['hessa.malik']), ('sara.qahtani', ['omar.shammari']), ('mona.dosari', []),
        ], 1):
            n = CallTreeNode.objects.create(call_tree=tree, user=self.u(mgr), parent=root, order=i, phone=self.u(mgr).profile.mobile)
            for j, r in enumerate(reports, 1):
                CallTreeNode.objects.create(call_tree=tree, user=self.u(r), parent=n, order=j, phone=self.u(r).profile.mobile)

        Y = self.today.year
        for iid, title, title_ar, itype, sev, status, rep, res, team, bcp, drp, funcs, desc in [
            ('INC-%d-001' % Y, 'Targeted phishing campaign against finance team', 'حملة تصيد موجهة لفريق المالية', 'cyber_attack', 'high', 'closed', -160, -158, irt, None, None, ['BF-007'],
             'Spear-phishing emails impersonating a vendor requested bank detail changes. Two users clicked; credentials reset within 1 hour.'),
            ('INC-%d-002' % Y, 'Utility power outage at primary data center', 'انقطاع التيار الكهربائي في مركز البيانات الرئيسي', 'infrastructure', 'critical', 'closed', -110, -109, cmt, 'BCP-002', 'DRP-001', ['BF-001', 'BF-002', 'BF-003'],
             'Grid outage for 6 hours; generator failed to start automatically, causing 40 minutes of downtime before manual start.'),
            ('INC-%d-003' % Y, 'Flash flooding restricting access to Riyadh HQ', 'سيول تعيق الوصول إلى المقر الرئيسي', 'natural_disaster', 'medium', 'closed', -75, -74, cmt, 'BCP-001', None, ['BF-004'],
             'Heavy rainfall closed roads around HQ; staff activated work-from-home arrangements for 1 day.'),
            ('INC-%d-004' % Y, 'DDoS attack on customer portal', 'هجوم حجب الخدمة على بوابة العملاء', 'cyber_attack', 'high', 'recovering', -3, None, irt, None, 'DRP-002', ['BF-003'],
             'Volumetric DDoS peaking at 40 Gbps; traffic scrubbing activated with upstream provider; intermittent latency persists.'),
            ('INC-%d-005' % Y, 'Payment gateway provider outage', 'انقطاع مزود بوابة الدفع', 'operational', 'critical', 'responding', -1, None, cmt, 'BCP-001', None, ['BF-002', 'BF-003'],
             'Third-party payment processor reports platform-wide outage; online payments failing. Customers notified via portal banner.'),
            ('INC-%d-006' % Y, 'Suspicious login activity on admin account', 'نشاط دخول مشبوه على حساب مسؤول', 'security', 'medium', 'assessing', 0, None, irt, None, None, [],
             'SIEM alert for impossible-travel login on a domain admin account; account disabled pending investigation.'),
        ]:
            reported = self.dt(rep, hours=-5)
            resolved = self.dt(res) if res is not None else None
            inc = CrisisIncident.objects.create(
                organization=self.org, incident_id=iid, title=title, title_ar=title_ar, incident_type=itype,
                severity=sev, status=status, description=desc,
                impact_description='Service degradation for customers and internal users; see BIA for financial estimates.',
                response_actions='Incident declared, team convened via call tree, containment and recovery actions executed.',
                crisis_team=team, incident_commander=team.members.filter(role='commander').first().user,
                activated_bc_plan=self.bcplans.get(bcp), activated_dr_plan=self.drplans.get(drp),
                reported_at=reported, declared_at=reported + timedelta(minutes=30), resolved_at=resolved,
                closed_at=(resolved + timedelta(days=3)) if (resolved and status == 'closed') else None,
                lessons_learned='Update runbooks; add automated alerting; repeat test within 90 days.' if status == 'closed' else '',
                reported_by=self.u('yousef.anazi'),
            )
            for f in funcs:
                inc.affected_functions.add(F[f])

        tests = [
            ('TST-%d-01' % Y, 'Annual Corporate BCP Tabletop Exercise', 'تمرين المحاكاة المكتبي لخطة الاستمرارية', 'tabletop', 'completed', 'BCP-001', None, -90, 'Pass with observations',
             'Prolonged loss of HQ building during Ramadan peak period.'),
            ('TST-%d-02' % Y, 'Data Center Failover Simulation', 'محاكاة التحويل لمركز البيانات الاحتياطي', 'simulation', 'completed', 'BCP-002', 'DRP-001', -120, 'Partial pass',
             'Complete loss of primary data center; failover to Jeddah DR site.'),
            ('TST-%d-03' % Y, 'Customer Portal DR Parallel Test', 'اختبار موازٍ لتعافي بوابة العملاء', 'parallel', 'completed', 'BCP-002', 'DRP-002', -60, 'Pass',
             'Regional cloud zone failure affecting customer portal.'),
            ('TST-%d-04' % Y, 'Ransomware Response Tabletop', 'تمرين محاكاة الاستجابة لهجوم الفدية', 'tabletop', 'planned', None, None, 21, '',
             'Ransomware encrypts file servers and ERP; attackers demand payment and threaten data leak.'),
            ('TST-%d-05' % Y, 'Call Tree Notification Test', 'اختبار شجرة الاتصال', 'walkthrough', 'completed', 'BCP-001', None, -45, 'Pass',
             'After-hours activation of the executive call tree.'),
            ('TST-%d-06' % Y, 'ERP Full Restore Test', 'اختبار الاستعادة الكاملة لنظام الموارد', 'full', 'planned', 'BCP-001', 'DRP-003', 40, '',
             'Restore ERP production from backup into isolated DR environment.'),
        ]
        self.tests = {}
        for tid, title, title_ar, ttype, status, bcp, drp, day, result, scenario in tests:
            done = status == 'completed'
            t = BCMTest.objects.create(
                organization=self.org, test_id=tid, title=title, title_ar=title_ar, test_type=ttype, status=status,
                objectives='Validate plan effectiveness, team readiness and ability to meet RTO/RPO.',
                scope='Crisis management team and functions covered by the selected plan.',
                bc_plan=self.bcplans.get(bcp), dr_plan=self.drplans.get(drp), scenario=scenario,
                scheduled_date=self.d(day), scheduled_duration_hours=4 if ttype in ('simulation', 'full', 'parallel') else 2,
                actual_start=self.dt(day) if done else None, actual_end=self.dt(day, hours=4) if done else None,
                coordinator=self.u('turki.juhani'), overall_result=result,
                results_summary='Objectives largely met; improvement actions identified.' if done else '',
                strengths_identified='Strong leadership engagement; clear communication.' if done else '',
                weaknesses_identified='Outdated contact details; some recovery steps undocumented.' if done else '',
                lessons_learned='Update call tree quarterly; document manual workarounds.' if done else '',
                created_by=self.u('turki.juhani'),
            )
            t.participants.add(*[self.u(x) for x in ['faisal.shahrani', 'khalid.otaibi', 'noura.zahrani', 'majed.ghamdi', 'yousef.anazi']])
            self.tests[tid] = t

        for tid, title, sev, status, rec, assignee, due in [
            ('TST-%d-01' % Y, '3 call tree contacts had outdated mobile numbers', 'medium', 'resolved', 'Implement quarterly contact verification.', 'turki.juhani', -60),
            ('TST-%d-01' % Y, 'Alternate site seating plan not defined', 'low', 'resolved', 'Agree seating allocation with facilities.', 'noura.zahrani', -50),
            ('TST-%d-02' % Y, 'Database failover exceeded RTO by 45 minutes', 'high', 'in_progress', 'Automate DNS switch and pre-stage database promotion scripts.', 'khalid.otaibi', 20),
            ('TST-%d-02' % Y, 'Generator automatic transfer switch failed', 'critical', 'resolved', 'Replace ATS and include in monthly maintenance test.', 'khalid.otaibi', -90),
            ('TST-%d-02' % Y, 'SIEM not available at DR site', 'medium', 'open', 'Deploy SIEM collector at DR site.', 'lama.malki', 45),
            ('TST-%d-03' % Y, 'CDN cache purge procedure not documented', 'low', 'accepted', 'Add step to DR runbook.', 'yousef.anazi', None),
        ]:
            BCMTestFinding.objects.create(
                test=self.tests[tid], title=title, description=f'Observed during test: {title.lower()}.', severity=sev,
                status=status, recommendation=rec, assigned_to=self.u(assignee),
                due_date=self.d(due) if due is not None else None,
                resolution='Action implemented and verified.' if status == 'resolved' else '',
                resolved_date=self.d((due or 0) - 2) if status == 'resolved' else None,
            )

    # ------------------------------------------------------------------ #
    # FRAMEWORKS APP (templates, mappings, regulatory requirements)
    # ------------------------------------------------------------------ #
    def seed_frameworks_app(self):
        for code, fw in self.frameworks.items():
            FrameworkTemplate.objects.create(
                code=code, name=fw.name, name_ar=fw.name_ar, version=fw.version, description=fw.description,
                template_data={'domains': [
                    {'code': d.code, 'name': d.name, 'controls': list(d.controls.values_list('control_id', flat=True))}
                    for d in fw.domains.all()
                ]},
            )
        for src, tgt, mtype in [('1-3', 'A.5.1', 'full'), ('1-4', 'A.5.2', 'full'), ('2-1', 'A.5.9', 'full'),
                                ('2-2', 'A.5.15', 'partial'), ('2-2', 'A.8.2', 'partial'), ('2-9', 'A.8.13', 'full'),
                                ('2-10', 'A.8.8', 'full'), ('2-12', 'A.8.15', 'partial'), ('2-13', 'A.5.24', 'partial'),
                                ('2-14', 'A.7.1', 'related'), ('4-1', 'A.5.19', 'full'), ('4-2', 'A.5.23', 'full'),
                                ('3-1', 'A.5.30', 'partial'), ('1-10', 'A.6.3', 'full')]:
            ControlMapping.objects.create(source_framework='NCA-ECC', source_control_id=src,
                                          target_framework='ISO27001', target_control_id=tgt, mapping_type=mtype)
        for code, rid, title, title_ar, rtype, ref, ctrls, desc in [
            ('PDPL', 'PDPL-R01', 'Obtain consent for processing where required', 'الحصول على الموافقة للمعالجة', 'mandatory', 'Chapter 2', ['PDPL-CTL-01'], 'Personal data shall not be processed without the consent of the data subject except in cases permitted by the Law.'),
            ('PDPL', 'PDPL-R02', 'Notify the authority of personal data breaches', 'إبلاغ الجهة المختصة عن التسريبات', 'mandatory', 'Chapter 3', ['PDPL-SEC-02'], 'The controller shall notify the competent authority upon becoming aware of a personal data breach, within the prescribed timeframe (72 hours under the Implementing Regulation).'),
            ('PDPL', 'PDPL-R03', 'Maintain records of processing activities', 'الاحتفاظ بسجل أنشطة المعالجة', 'mandatory', 'Chapter 3', ['PDPL-CTL-03'], 'The controller shall maintain a record of personal data processing activities.'),
            ('PDPL', 'PDPL-R04', 'Restrict cross-border transfers', 'تقييد نقل البيانات خارج المملكة', 'mandatory', 'Chapter 4', ['PDPL-SEC-03'], 'Transfer of personal data outside the Kingdom is permitted only under the conditions specified by the Law and its regulations.'),
            ('NCA-ECC', 'ECC-R01', 'Establish a dedicated cybersecurity function', 'إنشاء إدارة مستقلة للأمن السيبراني', 'mandatory', 'ECC 1-2', ['1-2'], 'A cybersecurity function independent from IT shall be established, reporting to the head of the organization.'),
            ('NCA-ECC', 'ECC-R02', 'Conduct periodic penetration testing', 'إجراء اختبارات الاختراق الدورية', 'mandatory', 'ECC 2-11', ['2-11'], 'Penetration tests shall be conducted periodically on internet-facing services and critical systems.'),
            ('SAMA-CSF', 'SAMA-R01', 'Board-approved cybersecurity strategy', 'استراتيجية أمن سيبراني معتمدة من المجلس', 'recommended', 'CSF 3.1.2', ['SAMA-3.1.2'], 'A cybersecurity strategy aligned with business objectives shall be defined and approved.'),
        ]:
            RegulatoryRequirement.objects.create(
                framework_code=code, requirement_id=rid, title=title, title_ar=title_ar, description=desc,
                requirement_type=rtype, article_reference=ref, related_control_ids=ctrls,
                penalty_description='Administrative fines and corrective orders may apply for non-compliance.' if rtype == 'mandatory' else '',
            )

    # ------------------------------------------------------------------ #
    # DASHBOARD KPIs
    # ------------------------------------------------------------------ #
    def seed_dashboard(self):
        # metric = key in core.automation.KPI_METRICS; the snapshot_kpis job computes the current month.
        kpis = [
            ('DEMO-COMP-SCORE', 'Overall Compliance Score', 'نسبة الامتثال الإجمالية', '%', 'up_good', 90, 75, 60, 'compliance_score', [61, 64, 67, 70, 72]),
            ('DEMO-HIGH-RISKS', 'Open High/Critical Risks', 'المخاطر العالية والحرجة المفتوحة', 'count', 'down_good', 3, 6, 10, 'open_high_risks', [14, 13, 13, 12, 12]),
            ('DEMO-OVERDUE-CAR', 'Overdue Corrective Actions', 'الإجراءات التصحيحية المتأخرة', 'count', 'down_good', 0, 3, 6, 'overdue_corrective_actions', [5, 4, 4, 3, 2]),
            ('DEMO-POL-REVIEW', 'Policies Reviewed On Time', 'السياسات المراجعة في موعدها', '%', 'up_good', 95, 85, 70, 'policies_reviewed_on_time_pct', [78, 80, 83, 85, 88]),
            ('DEMO-BCP-TESTED', 'Critical Functions with Tested Plans', 'الوظائف الحرجة ذات الخطط المختبرة', '%', 'up_good', 100, 80, 60, 'critical_functions_tested_pct', [50, 55, 60, 70, 75]),
            ('DEMO-PHISH-CLICK', 'Phishing Simulation Click Rate', 'نسبة النقر في محاكاة التصيد', '%', 'down_good', 5, 10, 20, None, [18, 15, 12, 11, 9, 7]),
        ]
        for code, name, name_ar, unit, trend, target, warn, crit, metric, series in kpis:
            kpi = KPI.objects.create(
                code=code, name=name, name_ar=name_ar, unit=unit, trend_direction=trend,
                target_value=Decimal(target), warning_threshold=Decimal(warn), critical_threshold=Decimal(crit),
                description=f'Monthly tracked KPI: {name}.' + (' Calculated automatically.' if metric else ' Entered manually.'),
                calculation_config={'metric': metric} if metric else {},
            )
            # Historical months are seeded; the current month comes from the snapshot_kpis job.
            first_of_month = self.today.replace(day=1)
            for i, v in enumerate(series):
                months_back = len(series) - i
                period = (first_of_month - timedelta(days=28 * months_back)).replace(day=1)
                KPIValue.objects.update_or_create(organization=self.org, kpi=kpi, period_date=period,
                                                  defaults={'value': Decimal(v)})

    # ------------------------------------------------------------------ #
    # LIVE WORKFLOWS: items created by Authors -> real pending approvals
    # ------------------------------------------------------------------ #
    def seed_live_workflows(self):
        from workflow.services import WorkflowService

        self.wf_items = []
        pol = Policy.objects.create(
            organization=self.org, category=PolicyCategory.objects.get(code='DEMO-OPS'), policy_id='POL-OPS-002',
            title='Social Media Usage Policy', title_ar='سياسة استخدام وسائل التواصل الاجتماعي',
            purpose='Define acceptable use of social media by employees when referring to the company.',
            scope='All employees and contractors.', policy_statement='Employees must not disclose confidential information on social media.',
            owner=self.u('hessa.malik'), department=self.dept('OPS'), created_by=self.u('hessa.malik'),
        )
        risk = Risk.objects.create(
            organization=self.org, category=RiskCategory.objects.get(code='DEMO-CYB'), risk_id=f'RSK-{self.today.year}-021',
            title='Abuse of privileged access by IT administrators', title_ar='إساءة استخدام الصلاحيات المميزة من قبل مسؤولي الأنظمة',
            description='Administrators with unrestricted access could alter logs or access sensitive data without detection.',
            risk_type='cyber', owner=self.u('lama.malki'), department=self.dept('CYBER'),
            inherent_likelihood=3, inherent_impact=5, identified_date=self.today, created_by=self.u('lama.malki'),
        )
        risk2 = Risk.objects.create(
            organization=self.org, category=RiskCategory.objects.get(code='DEMO-CMP'), risk_id=f'RSK-{self.today.year}-022',
            title='Late regulatory submissions due to manual data collection', title_ar='تأخر التقارير التنظيمية بسبب الجمع اليدوي للبيانات',
            description='Regulatory reports rely on spreadsheets compiled manually from several systems.',
            risk_type='compliance', owner=self.u('reem.subaie'), department=self.dept('COMP'),
            inherent_likelihood=3, inherent_impact=3, identified_date=self.d(-3), created_by=self.u('reem.subaie'),
        )
        bcp = BCPlan.objects.create(
            organization=self.org, plan_id='BCP-005', title='Contact Center Continuity Plan', title_ar='خطة استمرارية مركز الاتصال',
            scope='Customer contact center operations.', objectives='Restore inbound call handling within 4 hours.',
            owner=self.u('turki.juhani'), created_by=self.u('turki.juhani'),
        )
        bcp.covered_functions.add(self.functions['BF-004'])
        audit = Audit.objects.create(
            organization=self.org, audit_id=f'AUD-{self.today.year}-08', title='Internal Audit - Change Management',
            title_ar='مراجعة داخلية - إدارة التغيير', audit_type='internal', status='planned',
            scope='IT change management process and emergency changes.', planned_start_date=self.d(30),
            planned_end_date=self.d(44), lead_auditor=self.u('badr.saleh'), created_by=self.u('badr.saleh'),
        )
        audit.frameworks.add(self.frameworks['ISO27001'])
        proc = Procedure.objects.create(
            organization=self.org, policy=self.policies['POL-ISEC-003'], procedure_id='PRC-IAM-003',
            title='Privileged Access Management Procedure', title_ar='إجراء إدارة الصلاحيات المميزة',
            purpose='Control the request, approval and monitoring of privileged accounts.', scope='All administrative accounts.',
            procedure_steps='1. Request via PAM portal\n2. Approval by system owner\n3. Session recording enabled\n4. Monthly review',
            owner=self.u('yousef.anazi'), department=self.dept('IT'), created_by=self.u('yousef.anazi'),
        )
        RiskAcceptance.objects.create(
            risk=self.risks['R-019'], justification='Workloads affected are non-personal analytics data; relocation planned next fiscal year.',
            accepted_likelihood=2, accepted_impact=3, status='pending', valid_from=self.today, valid_until=self.d(180),
            requested_by=self.u('omar.shammari'), requested_date=self.today,
        )

        # One approved and one rejected to populate workflow history
        for obj, decision, user, comment in [
            (risk2, 'approved', 'fahad.harbi', 'Valid risk. Please add treatment plan for automation of reporting.'),
            (proc, 'rejected', 'khalid.otaibi', 'Please add break-glass account handling and align with PAM tool workflow.'),
        ]:
            wf = WorkflowService.get_workflow_for_object(obj)
            approval = wf.approvals.filter(status='pending').first() if wf else None
            if approval:
                WorkflowService.handle_approval_decision(approval, decision, self.u(user), comment)

    # ------------------------------------------------------------------ #
    def seed_tasks_and_notifications(self):
        from django.core.management import call_command
        call_command('loaddata', 'notification_templates', verbosity=0)

        tasks = [
            ('Collect Q4 access review evidence', 'جمع أدلة مراجعة الصلاحيات للربع الرابع', 'evidence', 'high', 'in_progress', 'lama.malki', 'majed.ghamdi', 7),
            ('Update BIA for Customer Contact Center', 'تحديث تحليل أثر الأعمال لمركز الاتصال', 'assessment', 'medium', 'pending', 'turki.juhani', 'faisal.shahrani', 14),
            ('Remediate finding: leaver accounts still active', 'معالجة ملاحظة: حسابات الموظفين المغادرين', 'remediation', 'critical', 'in_progress', 'yousef.anazi', 'khalid.otaibi', 3),
            ('Review Cryptography Policy draft', 'مراجعة مسودة سياسة التشفير', 'review', 'medium', 'pending', 'fahad.harbi', 'majed.ghamdi', 10),
            ('Prepare evidence pack for NCA ECC assessment', 'إعداد حزمة الأدلة لتقييم الضوابط الأساسية', 'audit', 'high', 'in_progress', 'reem.subaie', 'fahad.harbi', 12),
            ('Quarterly risk register review', 'المراجعة الربعية لسجل المخاطر', 'review', 'high', 'pending', 'omar.shammari', 'sara.qahtani', 5),
            ('Schedule ransomware tabletop exercise', 'جدولة تمرين محاكاة هجوم الفدية', 'general', 'medium', 'completed', 'turki.juhani', 'faisal.shahrani', -5),
            ('Restore test for ERP backups', 'اختبار استعادة نسخ نظام الموارد', 'remediation', 'high', 'overdue', 'yousef.anazi', 'khalid.otaibi', -4),
            ('Update ROPA after new CRM onboarding', 'تحديث سجل أنشطة المعالجة بعد إضافة نظام CRM', 'general', 'medium', 'pending', 'nawaf.mutairi', 'fahad.harbi', 20),
            ('Phishing simulation - November campaign', 'محاكاة التصيد - حملة نوفمبر', 'general', 'low', 'completed', 'lama.malki', 'majed.ghamdi', -10),
            ('Vendor assessment: new cloud hosting provider', 'تقييم مورد: مزود الاستضافة السحابية الجديد', 'assessment', 'high', 'pending', 'omar.shammari', 'sara.qahtani', 9),
        ]
        for title, title_ar, ttype, prio, status, to, by, due in tasks:
            Task.objects.create(
                title=title, title_ar=title_ar, task_type=ttype, priority=prio, status=status,
                description=f'{title}. Please update progress in the system.', assigned_to=self.u(to), assigned_by=self.u(by),
                due_date=self.dt(due), started_at=self.dt(-3) if status in ('in_progress', 'completed', 'overdue') else None,
                completed_at=self.dt(due) if status == 'completed' else None,
                completion_notes='Done and evidence uploaded.' if status == 'completed' else '',
            )

        recipients = list(self.users.values()) + list(User.objects.filter(is_superuser=True))
        msgs = [
            ('Evidence expiring soon', '3 evidence items for NCA ECC controls expire within 30 days.', 'high'),
            ('Policy review due', 'Information Security Policy is due for annual review next month.', 'normal'),
            ('BCM test scheduled', 'Ransomware Response Tabletop is scheduled in 3 weeks.', 'normal'),
            ('Critical incident declared', 'INC: Payment gateway provider outage - Crisis Management Team activated.', 'urgent'),
        ]
        for user in recipients:
            for subject, body, prio in self.rng.sample(msgs, 2):
                Notification.objects.create(
                    recipient=user, subject=subject, body=body, priority=prio, channel='in_app',
                    status=self.rng.choice(['sent', 'sent', 'read']), sent_at=self.dt(-self.rng.randint(0, 5)),
                )

    # ------------------------------------------------------------------ #
    def print_summary(self):
        rows = [
            ('Users', User.objects.filter(email__endswith=f'@{DEMO_EMAIL_DOMAIN}').count()),
            ('Departments', Department.objects.filter(organization=self.org).count()),
            ('Policies / Procedures / Documents', f'{Policy.objects.filter(organization=self.org).count()} / '
                                                  f'{Procedure.objects.filter(organization=self.org).count()} / '
                                                  f'{Document.objects.filter(organization=self.org).count()}'),
            ('Assets / Risks', f'{Asset.objects.filter(organization=self.org).count()} / {Risk.objects.filter(organization=self.org).count()}'),
            ('Risk assessments / treatments', f'{RiskAssessment.objects.filter(risk__organization=self.org).count()} / '
                                              f'{RiskTreatment.objects.filter(risk__organization=self.org).count()}'),
            ('Frameworks / Controls', f'{len(self.frameworks)} / {len(self.controls)}'),
            ('Evidence', Evidence.objects.filter(organization=self.org).count()),
            ('Audits / Findings / CARs', f'{Audit.objects.filter(organization=self.org).count()} / '
                                         f'{AuditFinding.objects.filter(audit__organization=self.org).count()} / '
                                         f'{CorrectiveAction.objects.filter(organization=self.org).count()}'),
            ('Business functions / BIAs', f'{BusinessFunction.objects.filter(organization=self.org).count()} / '
                                          f'{BusinessImpactAnalysis.objects.filter(organization=self.org).count()}'),
            ('BC plans / DR plans', f'{BCPlan.objects.filter(organization=self.org).count()} / '
                                    f'{DisasterRecoveryPlan.objects.filter(organization=self.org).count()}'),
            ('Incidents / BCM tests', f'{CrisisIncident.objects.filter(organization=self.org).count()} / '
                                      f'{BCMTest.objects.filter(organization=self.org).count()}'),
            ('Workflow instances (pending)', f'{WorkflowInstance.objects.count()} '
                                             f'({WorkflowInstance.objects.filter(status="in_progress").count()})'),
            ('Tasks / Notifications', f'{Task.objects.count()} / {Notification.objects.count()}'),
        ]
        self.stdout.write(self.style.SUCCESS('\nDemo data created:'))
        for k, v in rows:
            self.stdout.write(f'  {k:<36} {v}')
        self.stdout.write(f'\nAll demo users share the password: {self.password}')
        self.stdout.write('  Managers: khalid.otaibi, majed.ghamdi, sara.qahtani, fahad.harbi, faisal.shahrani, ...')
        self.stdout.write('  Authors : omar.shammari, reem.subaie, badr.saleh, yousef.anazi, lama.malki, turki.juhani, hessa.malik')
