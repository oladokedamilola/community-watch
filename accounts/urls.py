# accounts/urls.py
from django.urls import path
from .views import auth_views, general_views

app_name = 'accounts'

urlpatterns = [
    # ===== AUTHENTICATION VIEWS =====
    path('register/', auth_views.register_view, name='register'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    
    #==== PASSWORD SETUP (for new users) =====
    path('password-setup/', auth_views.password_setup_request_view, name='password_setup_request'),
    path('password-setup/<uuid:token>/', auth_views.password_setup_confirm_view, name='password_setup_confirm'),
    
    # ===== EMAIL VERIFICATION =====
    path('verify-email/<uuid:token>/', auth_views.verify_email_view, name='verify_email'),
    path('resend-verification/', auth_views.resend_verification_view, name='resend_verification'),
    path('pending-verification/', auth_views.pending_verification_view, name='pending_verification'),
    
    # ===== PASSWORD MANAGEMENT =====
    path('password-reset/', auth_views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/<uuid:token>/', auth_views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password-change/', auth_views.password_change_view, name='password_change'),
    
    # ===== PROFILE & GENERAL =====
    path('profile/', general_views.profile_view, name='profile'),
    path('dashboard/', general_views.dashboard_view, name='dashboard'),
    path('upload-profile-picture/', general_views.upload_profile_picture, name='upload_profile_picture'),
    
    # ===== AJAX ENDPOINTS =====
    path('check-username/', auth_views.check_username, name='check_username'),
    path('check-email/', auth_views.check_email, name='check_email'),
]