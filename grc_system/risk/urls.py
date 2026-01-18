"""
Risk app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'asset-categories', views.AssetCategoryViewSet)
router.register(r'assets', views.AssetViewSet)
router.register(r'risk-categories', views.RiskCategoryViewSet)
router.register(r'risks', views.RiskViewSet)
router.register(r'assessments', views.RiskAssessmentViewSet)
router.register(r'treatments', views.RiskTreatmentViewSet)
router.register(r'acceptances', views.RiskAcceptanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
