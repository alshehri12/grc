"""
BCM app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'functions', views.BusinessFunctionViewSet)
router.register(r'bia', views.BusinessImpactAnalysisViewSet)
router.register(r'bc-plans', views.BCPlanViewSet)
router.register(r'dr-plans', views.DisasterRecoveryPlanViewSet)
router.register(r'crisis-teams', views.CrisisManagementTeamViewSet)
router.register(r'crisis-members', views.CrisisTeamMemberViewSet)
router.register(r'call-trees', views.CallTreeViewSet)
router.register(r'incidents', views.CrisisIncidentViewSet)
router.register(r'tests', views.BCMTestViewSet)
router.register(r'test-findings', views.BCMTestFindingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
