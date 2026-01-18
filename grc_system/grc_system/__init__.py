"""
GRC System - Governance, Risk & Compliance Platform
نظام الحوكمة والمخاطر والامتثال
"""

# Load Celery app when Django starts
from .celery import app as celery_app

__all__ = ('celery_app',)
