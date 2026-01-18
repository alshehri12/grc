"""
Workflow app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.WorkflowTemplateViewSet)
router.register(r'steps', views.WorkflowStepViewSet)
router.register(r'instances', views.WorkflowInstanceViewSet)
router.register(r'approvals', views.ApprovalViewSet)
router.register(r'tasks', views.TaskViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
