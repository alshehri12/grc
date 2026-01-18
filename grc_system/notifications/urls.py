"""
Notifications app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.NotificationTemplateViewSet)
router.register(r'notifications', views.NotificationViewSet)
router.register(r'reminders', views.ReminderViewSet)
router.register(r'escalations', views.EscalationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
