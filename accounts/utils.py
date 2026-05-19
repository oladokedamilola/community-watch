from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


def send_verification_email(user, token_obj):
    """Send email verification link to user"""
    try:
        verification_url = f"{settings.SITE_URL}{reverse('accounts:verify_email', args=[token_obj.token])}"
        
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'GridWatch',
            'expiry_hours': getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24),
        }
        
        html_message = render_to_string('accounts/emails/verification_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Verify your email address - GridWatch',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        raise


def send_password_reset_email(user, token_obj):
    """Send password reset link to user"""
    try:
        reset_url = f"{settings.SITE_URL}{reverse('accounts:password_reset_confirm', args=[token_obj.token])}"
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'GridWatch',
            'expiry_hours': getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_HOURS', 1),
        }
        
        html_message = render_to_string('accounts/emails/password_reset_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Reset your password - GridWatch',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        raise


def send_welcome_email(user):
    """Send welcome email to new user"""
    try:
        context = {
            'user': user,
            'site_name': 'GridWatch',
            'login_url': f"{settings.SITE_URL}{reverse('accounts:login')}",
            'dashboard_url': f"{settings.SITE_URL}{reverse('reports:community_dashboard')}",
        }
        
        html_message = render_to_string('accounts/emails/welcome_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Welcome to GridWatch!',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        raise
    
    
def send_password_setup_email(user, token_obj):
    """Send password setup link to social auth user"""
    try:
        setup_url = f"{settings.SITE_URL}{reverse('accounts:password_setup', args=[token_obj.token])}"
        
        context = {
            'user': user,
            'setup_url': setup_url,
            'site_name': 'GridWatch',
            'expiry_hours': getattr(settings, 'PASSWORD_SETUP_TOKEN_EXPIRY_HOURS', 24),
        }
        
        html_message = render_to_string('accounts/emails/password_setup_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Set up your password - GridWatch',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password setup email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password setup email to {user.email}: {str(e)}")
        raise
    
    
    
def send_password_setup_email(user, token_obj):
    """Send password setup link to social auth user"""
    try:
        setup_url = f"{settings.SITE_URL}{reverse('accounts:password_setup_confirm', args=[token_obj.token])}"
        
        context = {
            'user': user,
            'setup_url': setup_url,
            'site_name': 'GridWatch',
            'expiry_hours': getattr(settings, 'PASSWORD_SETUP_TOKEN_EXPIRY_HOURS', 24),
        }
        
        html_message = render_to_string('accounts/emails/password_setup_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Set up your password - GridWatch',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password setup email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password setup email to {user.email}: {str(e)}")
        raise