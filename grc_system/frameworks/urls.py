"""
Frameworks app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.FrameworkTemplateViewSet)
router.register(r'mappings', views.ControlMappingViewSet)
router.register(r'requirements', views.RegulatoryRequirementViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
