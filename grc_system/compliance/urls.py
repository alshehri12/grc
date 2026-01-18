"""
Compliance app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'frameworks', views.ControlFrameworkViewSet)
router.register(r'domains', views.ControlDomainViewSet)
router.register(r'controls', views.ControlViewSet)
router.register(r'implementations', views.ControlImplementationViewSet)
router.register(r'audits', views.AuditViewSet)
router.register(r'findings', views.AuditFindingViewSet)
router.register(r'corrective-actions', views.CorrectiveActionViewSet)
router.register(r'evidence', views.EvidenceViewSet)
router.register(r'gap-assessments', views.GapAssessmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
