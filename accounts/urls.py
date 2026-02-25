"""
URLs للحسابات
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    # التسجيل وتسجيل الدخول
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # JWT Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # الملف الشخصي
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    
    # كلمة المرور
    path('password/change/', views.change_password_view, name='change_password'),
    path('password/reset/request/', views.password_reset_request_view, name='password_reset_request'),
    path('password/reset/confirm/', views.password_reset_confirm_view, name='password_reset_confirm'),
    
    # التوثيق
    path('verify-email/', views.verify_email_view, name='verify_email'),
    
    # السجلات
    path('login-history/', views.login_history_view, name='login_history'),
    
    # حذف الحساب
    path('delete/', views.delete_account_view, name='delete_account'),
]
