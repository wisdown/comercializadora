from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core.views.auth_views import CambiarPasswordView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Rutas de autenticación JWT
    path("api/v1/auth/login", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/cambiar-password", CambiarPasswordView.as_view()),
    # Rutas principales de tu app core
    path("api/v1/", include("core.urls")),
]
