"""
Django settings for GRC System project.
Enterprise GRC (Governance, Risk, Compliance) Platform
Supports Arabic/English with RTL layout.
"""
import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-sb$p_4nht0+h@(mc1yux8h%(!!)=8p+++pfq1(h4d%qwsw=igs')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    'django_celery_results',
    
    # GRC System apps
    'core.apps.CoreConfig',
    'workflow.apps.WorkflowConfig',
    'notifications.apps.NotificationsConfig',
    'governance.apps.GovernanceConfig',
    'risk.apps.RiskConfig',
    'bcm.apps.BcmConfig',
    'compliance.apps.ComplianceConfig',
    'frameworks.apps.FrameworksConfig',
    'dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'grc_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'grc_system.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization - Arabic/English support
LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# Simple JWT configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS configuration for Vue.js frontend
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Allow all origins in development
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS', 
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000'
).split(',')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Celery configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Periodic automation (see core/automation.py). DatabaseScheduler imports this
# schedule on start-up. Without Celery: `python manage.py run_automation` from cron.
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'deliver-notifications':      {'task': 'grc.automation.deliver_notifications',      'schedule': crontab(minute='*/5')},
    'escalate-overdue-approvals': {'task': 'grc.automation.escalate_overdue_approvals', 'schedule': crontab(minute=0)},
    'process-escalations':        {'task': 'grc.automation.process_escalations',        'schedule': crontab(minute=10)},
    'mark-overdue-items':         {'task': 'grc.automation.mark_overdue_items',         'schedule': crontab(minute=20)},
    'remind-upcoming-approvals':  {'task': 'grc.automation.remind_upcoming_approvals',  'schedule': crontab(hour=7, minute=0)},
    'send-review-reminders':      {'task': 'grc.automation.send_review_reminders',      'schedule': crontab(hour=7, minute=15)},
    'expire-evidence':            {'task': 'grc.automation.expire_evidence',            'schedule': crontab(hour=6, minute=0)},
    'expire-risk-acceptances':    {'task': 'grc.automation.expire_risk_acceptances',    'schedule': crontab(hour=6, minute=15)},
    'recalculate-residual-risks': {'task': 'grc.automation.recalculate_residual_risks', 'schedule': crontab(hour=2, minute=0)},
    'refresh-gap-assessments':    {'task': 'grc.automation.refresh_gap_assessments',    'schedule': crontab(hour=3, minute=0)},
    'snapshot-kpis':              {'task': 'grc.automation.snapshot_kpis',              'schedule': crontab(hour=4, minute=0)},
}

# Thresholds used by the automation jobs (days). Override via environment if needed.
GRC_AUTOMATION = {
    'REVIEW_WARNING_DAYS': int(os.environ.get('GRC_REVIEW_WARNING_DAYS', 30)),
    'RISK_REVIEW_WARNING_DAYS': int(os.environ.get('GRC_RISK_REVIEW_WARNING_DAYS', 14)),
    'EVIDENCE_WARNING_DAYS': int(os.environ.get('GRC_EVIDENCE_WARNING_DAYS', 30)),
    'ACCEPTANCE_WARNING_DAYS': int(os.environ.get('GRC_ACCEPTANCE_WARNING_DAYS', 30)),
    'PLAN_TEST_INTERVAL_DAYS': int(os.environ.get('GRC_PLAN_TEST_INTERVAL_DAYS', 365)),
    'BIA_REVIEW_INTERVAL_DAYS': int(os.environ.get('GRC_BIA_REVIEW_INTERVAL_DAYS', 365)),
    'UPCOMING_EVENT_DAYS': int(os.environ.get('GRC_UPCOMING_EVENT_DAYS', 7)),
    'REMINDER_DEDUPE_DAYS': int(os.environ.get('GRC_REMINDER_DEDUPE_DAYS', 7)),
    'EMAIL_ENABLED': os.environ.get('GRC_EMAIL_ENABLED', 'True').lower() == 'true',
}
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')

# Email configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'GRC System <noreply@grc.local>')

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'grc.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'grc': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory
(BASE_DIR / 'logs').mkdir(exist_ok=True)
