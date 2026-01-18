# GRC System - Governance, Risk & Compliance Platform

A comprehensive enterprise-grade GRC (Governance, Risk, and Compliance) management system built with Django REST Framework and Vue.js. Designed to help organizations manage their security frameworks, risk assessments, compliance audits, and business continuity planning in one unified platform.

![Dashboard](screenshots/dashboard.png)

## Why This Project?

Managing GRC activities across multiple spreadsheets and documents is a nightmare. I've seen teams struggle with scattered policies, missed audit deadlines, and risks that slip through the cracks. This platform brings everything together - from your ISO 27001 controls to your business continuity plans - in a single, streamlined interface.

## Key Features

### 🏛️ Governance Module
- Policy lifecycle management (draft → review → approval → publish)
- Procedure documentation linked to policies
- Document repository with version control
- Automated review reminders

![Policies](screenshots/policies.png)

### ⚠️ Risk Management
- Comprehensive risk register
- Risk assessment with likelihood/impact matrix
- Treatment plans and tracking
- Risk acceptance workflow
- Visual risk heatmap

![Risk Matrix](screenshots/risk-matrix.png)

### ✅ Compliance Management
- Multi-framework support (ISO 27001, NCA ECC, SAMA CSF, PDPL)
- Control implementation tracking
- Gap analysis and remediation
- Audit planning and execution
- Evidence collection and management
- Finding tracking with corrective actions

### 🔄 Business Continuity (BCM)
- Business Impact Analysis (BIA)
- Business Continuity Plans (BCP)
- Disaster Recovery Plans (DRP)
- Crisis management with call trees
- Testing and exercise management
- Incident tracking

![BCM](screenshots/bcm.png)

### 📊 Dashboard & Reporting
- Real-time compliance status
- Risk trends and analytics
- Upcoming deadlines and tasks
- Audit findings summary

## Tech Stack

**Backend:**
- Python 3.9+
- Django 4.2
- Django REST Framework
- Celery + Redis (for async tasks)
- SQLite (dev) / PostgreSQL (prod)

**Frontend:**
- Vue 3 (Composition API)
- PrimeVue UI Components
- Tailwind CSS
- Pinia (state management)
- Vue Router

**Other:**
- JWT Authentication
- Full RTL support (Arabic/English bilingual)

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Redis (for Celery tasks)

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/alshehri12/grc.git
cd grc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd grc_system
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

### Frontend Setup

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`

## Project Structure

```
grc/
├── grc_system/              # Django backend
│   ├── core/                # Users, organizations, departments
│   ├── governance/          # Policies, procedures, documents
│   ├── risk/                # Risk register, assessments, treatments
│   ├── compliance/          # Controls, audits, evidence
│   ├── bcm/                 # Business continuity management
│   ├── frameworks/          # Compliance frameworks (ISO, NCA, etc.)
│   ├── workflow/            # Tasks and approvals
│   ├── notifications/       # Alerts and reminders
│   └── dashboard/           # Analytics and reporting
│
├── frontend/                # Vue.js frontend
│   ├── src/
│   │   ├── views/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── stores/          # Pinia stores
│   │   ├── api/             # API client
│   │   ├── i18n/            # Translations (EN/AR)
│   │   └── router/          # Route definitions
│   └── ...
│
└── README.md
```

## Supported Frameworks

| Framework | Description |
|-----------|-------------|
| ISO 27001 | Information Security Management System |
| NCA ECC | Saudi National Cybersecurity Authority - Essential Cybersecurity Controls |
| SAMA CSF | Saudi Central Bank - Cyber Security Framework |
| PDPL | Personal Data Protection Law (Saudi) |

## Language Support

The platform fully supports **English** and **Arabic** languages with complete RTL (Right-to-Left) layout support. Users can switch between languages from the settings page.

## API Documentation

API endpoints follow RESTful conventions:

- `GET /api/risk/risks/` - List all risks
- `POST /api/risk/risks/` - Create new risk
- `GET /api/risk/risks/{id}/` - Get risk details
- `PUT /api/risk/risks/{id}/` - Update risk
- `DELETE /api/risk/risks/{id}/` - Delete risk
- `GET /api/risk/risks/matrix/` - Get risk matrix data
- `GET /api/risk/risks/statistics/` - Get risk statistics

Similar patterns apply to governance, compliance, and bcm modules.

## Default Credentials

After running migrations, create a superuser:

```bash
python manage.py createsuperuser
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

## License

[MIT](LICENSE)

## Roadmap

- [ ] Email notifications integration
- [ ] PDF report generation
- [ ] Automated compliance scanning
- [ ] Integration with vulnerability scanners
- [ ] Mobile app (React Native)
- [ ] Multi-tenant support

---

Built with ☕ and late nights. If you find this useful, give it a ⭐!
