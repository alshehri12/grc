"""
GRC System - Governance, Risk & Compliance Platform
نظام الحوكمة والمخاطر والامتثال
"""

# Load Celery app when Django starts (optional)
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed, skip loading
    celery_app = None
    __all__ = ()
