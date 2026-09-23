"""
URL configuration for medic project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .health import SystemHealthView


class LoginRateThrottle(AnonRateThrottle):
    """
    Phase 8: Scoped throttle for the /api/token/ login endpoint.
    Limits anonymous login attempts to 5 per minute to slow brute-force.
    Rate configured by DEFAULT_THROTTLE_RATES['login'] in settings.
    """
    scope = "login"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """TokenObtainPairView with login-specific throttle applied."""
    throttle_classes = [LoginRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    """TokenRefreshView with login-specific throttle applied."""
    throttle_classes = [LoginRateThrottle]


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/', include('monitoring.urls')),
    path('api/', include('accounts.urls')),
    path('api/', include('medication.urls')),
    path('api/', include('alerts.urls')),
    path('api/', include('communication.urls')),

    # Phase 8: throttled JWT endpoints (5 attempts/min to slow brute-force)
    path('api/token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', ThrottledTokenRefreshView.as_view(), name='token_refresh'),

    path("health/", SystemHealthView.as_view()),
]

# Note: Public static MEDIA_URL serving has been removed for medical privacy.
# Wound images are served strictly via authenticated, permission-checked API endpoints.
