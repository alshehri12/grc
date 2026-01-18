"""
URL configuration for GRC System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # JWT Authentication
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API routes
    path('api/core/', include('core.urls')),
    path('api/workflow/', include('workflow.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/governance/', include('governance.urls')),
    path('api/risk/', include('risk.urls')),
    path('api/bcm/', include('bcm.urls')),
    path('api/compliance/', include('compliance.urls')),
    path('api/frameworks/', include('frameworks.urls')),
    path('api/dashboard/', include('dashboard.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = 'GRC System Administration'
admin.site.site_title = 'GRC Admin'
admin.site.index_title = 'نظام الحوكمة والمخاطر والامتثال'
