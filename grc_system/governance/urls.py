"""
Governance app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.PolicyCategoryViewSet)
router.register(r'policies', views.PolicyViewSet)
router.register(r'versions', views.PolicyVersionViewSet)
router.register(r'acknowledgments', views.PolicyAcknowledgmentViewSet)
router.register(r'procedures', views.ProcedureViewSet)
router.register(r'documents', views.DocumentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
