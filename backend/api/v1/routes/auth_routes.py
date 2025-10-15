"""Auth routes - Authentication URL configuration"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from layers.controllers import auth_controller

urlpatterns = [
    # Authentication endpoints
    path('login/', auth_controller.login, name='auth-login'),
    path('logout/', auth_controller.logout, name='auth-logout'),
    path('me/', auth_controller.me, name='auth-me'),
    path('change-password/', auth_controller.change_password, name='auth-change-password'),
    
    # JWT token refresh
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
]