"""
Dashboard app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'widgets', views.DashboardWidgetViewSet)
router.register(r'dashboards', views.DashboardViewSet)
router.register(r'report-templates', views.ReportTemplateViewSet)
router.register(r'reports', views.GeneratedReportViewSet)
router.register(r'kpis', views.KPIViewSet)
router.register(r'kpi-values', views.KPIValueViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
