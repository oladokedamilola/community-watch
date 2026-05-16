# reports/notification_service.py
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Notification, EmailLog, OutageReport, PushSubscription
import logging
import json
import requests

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """Centralized notification service for all communications"""
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user"""
        subject = "Welcome to GridWatch! 🎉"
        
        context = {
            'user': user,
            'site_url': settings.SITE_URL,
            'login_url': f"{settings.SITE_URL}/accounts/login/"
        }
        
        html_content = render_to_string('emails/welcome.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            EmailLog.objects.create(
                recipient=user.email,
                subject=subject,
                notification_type='welcome'
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {e}")
            EmailLog.objects.create(
                recipient=user.email,
                subject=subject,
                notification_type='welcome',
                status='failed',
                error_message=str(e)
            )
            return False
    
    @staticmethod
    def send_report_confirmation(report, user=None):
        """Send confirmation email after report submission - notifying user that admin will review"""
        subject = f"GridWatch: Report Received - {report.report_id}"
        
        recipient_email = None
        if user and user.email:
            recipient_email = user.email
        elif report.contact_info and '@' in report.contact_info:
            recipient_email = report.contact_info
        
        if not recipient_email:
            return False
        
        context = {
            'report': report,
            'user': user,
            'site_url': settings.SITE_URL,
            'tracking_url': f"{settings.SITE_URL}/reports/track/{report.report_id}/"
        }
        
        html_content = render_to_string('emails/report_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            EmailLog.objects.create(
                recipient=recipient_email,
                subject=subject,
                notification_type='report_submitted',
                report=report
            )
            
            # Also create in-app notification for the user
            if user:
                NotificationService.create_inapp_notification(
                    user=user,
                    notification_type='report_submitted',
                    title='Report Received ✓',
                    message=f'Thank you for reporting. An admin will review your report {report.report_id} shortly.',
                    link=f'/reports/track/{report.report_id}/',
                    report=report
                )
            return True
        except Exception as e:
            logger.error(f"Failed to send report confirmation: {e}")
            return False
    
    @staticmethod
    def send_status_update_email(report, old_status, new_status, admin_notes=None):
        """Send email notification when report status changes"""
        logger.info(f"Starting send_status_update_email for report {report.report_id}")
        logger.info(f"Report user: {report.user}")
        logger.info(f"Report user email: {report.user.email if report.user else 'None'}")
        
        if not report.user or not report.user.email:
            logger.warning(f"Cannot send status update: No user or email for report {report.report_id}")
            return False
        
        subject = f"GridWatch: Update on {report.report_id} - {report.get_status_display()}"
        
        status_messages = {
            'verified': '✅ Your report has been verified by our team.',
            'in_progress': '🔧 Good news! Technical teams have been assigned to address the issue.',
            'resolved': '✔️ Great news! The outage has been resolved.',
            'rejected': '❌ Your report could not be verified at this time.'
        }
        
        context = {
            'report': report,
            'user': report.user,
            'old_status': old_status,
            'new_status': new_status,
            'status_message': status_messages.get(new_status, ''),
            'admin_notes': admin_notes,
            'site_url': settings.SITE_URL,
            'tracking_url': f"{settings.SITE_URL}/reports/track/{report.report_id}/"
        }
        
        # Send email
        try:
            html_content = render_to_string('emails/status_update.html', context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[report.user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            EmailLog.objects.create(
                recipient=report.user.email,
                subject=subject,
                notification_type='status_update',
                report=report
            )
            logger.info(f"Status update email sent to {report.user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send status update email to {report.user.email}: {e}")
            # Continue to create in-app notification even if email fails
        
        # Create in-app notification
        try:
            notification = NotificationService.create_inapp_notification(
                user=report.user,
                notification_type='status_update',
                title=f'Status Update - {report.get_status_display()}',
                message=f'Report {report.report_id} status changed to {report.get_status_display()}.',
                link=f'/reports/track/{report.report_id}/',
                report=report
            )
            
            if notification:
                logger.info(f"In-app notification created for {report.user.email}")
            else:
                logger.error(f"Failed to create in-app notification for {report.user.email}")
                
        except Exception as e:
            logger.error(f"Error creating in-app notification: {e}")
        
        # Send web push notification
        try:
            NotificationService.send_web_push(report.user, {
                'title': f'Status Update: {report.report_id}',
                'body': f'Your report is now {report.get_status_display()}',
                'icon': '/static/images/icon-192.png',
                'url': f'/reports/track/{report.report_id}/'
            })
            logger.info(f"Web push notification queued for {report.user.email}")
        except Exception as e:
            logger.error(f"Error sending web push: {e}")
        
        return True
    
    @staticmethod
    def send_resolution_notice(report):
        """Send resolution notice when outage is fixed"""
        subject = f"GridWatch: Outage Resolved - {report.report_id}"
        
        if not report.user or not report.user.email:
            return False
        
        context = {
            'report': report,
            'user': report.user,
            'site_url': settings.SITE_URL,
            'resolution_notes': report.resolution_notes
        }
        
        html_content = render_to_string('emails/resolution.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[report.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            EmailLog.objects.create(
                recipient=report.user.email,
                subject=subject,
                notification_type='report_resolved',
                report=report
            )
            
            NotificationService.create_inapp_notification(
                user=report.user,
                notification_type='report_resolved',
                title='Outage Resolved ✓',
                message=f'The outage in {report.location_text} has been resolved.',
                link=f'/reports/track/{report.report_id}/',
                report=report
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send resolution notice: {e}")
            return False
    
    @staticmethod
    def create_inapp_notification(user, notification_type, title, message, link=None, report=None):
        """Create an in-app notification"""
        try:
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                report=report
            )
            return notification
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {e}")
            return None
    
    @staticmethod
    def send_web_push(user, data):
        """Send web push notification using VAPID"""
        subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
        
        if not subscriptions.exists():
            return
        
        vapid_public_key = settings.WEBPUSH_SETTINGS.get('VAPID_PUBLIC_KEY')
        vapid_private_key = settings.WEBPUSH_SETTINGS.get('VAPID_PRIVATE_KEY')
        vapid_admin_email = settings.WEBPUSH_SETTINGS.get('VAPID_ADMIN_EMAIL')
        
        for subscription in subscriptions:
            try:
                # Prepare push payload
                payload = json.dumps({
                    'title': data.get('title', 'GridWatch Update'),
                    'body': data.get('body', ''),
                    'icon': data.get('icon', '/static/images/icon-192.png'),
                    'badge': '/static/images/badge.png',
                    'data': {
                        'url': data.get('url', '/'),
                        'timestamp': int(__import__('time').time())
                    },
                    'vibrate': [200, 100, 200],
                    'requireInteraction': False
                })
                
                # Web Push API request
                # Note: In production, use a library like pywebpush
                # For now, we'll log the attempt
                logger.info(f"Web push would be sent to {user.email}: {payload}")
                
                # Actual implementation would use:
                # from pywebpush import webpush
                # webpush(
                #     subscription_info={
                #         'endpoint': subscription.endpoint,
                #         'keys': {
                #             'p256dh': subscription.p256dh,
                #             'auth': subscription.auth
                #         }
                #     },
                #     data=payload,
                #     vapid_private_key=vapid_private_key,
                #     vapid_claims={
                #         'sub': f'mailto:{vapid_admin_email}'
                #     }
                # )
                
            except Exception as e:
                logger.error(f"Failed to send web push: {e}")
                # Mark subscription as inactive if it fails
                if '410' in str(e) or '404' in str(e):
                    subscription.is_active = False
                    subscription.save()
    
    @staticmethod
    def send_bulk_notification(users, title, message, notification_type='admin_message'):
        """Send notification to multiple users"""
        sent_count = 0
        for user in users:
            NotificationService.create_inapp_notification(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message
            )
            sent_count += 1
        return sent_count
    

    @staticmethod
    def notify_admins_new_report(report):
        """Notify all admin users about a new report submission"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get all admin users
        admin_users = User.objects.filter(is_admin=True, is_active=True)
        
        if not admin_users.exists():
            return
        
        # Create notification for each admin
        for admin in admin_users:
            NotificationService.create_inapp_notification(
                user=admin,
                notification_type='admin_message',
                title='New Report Submitted',
                message=f'A new report {report.report_id} has been submitted by {report.user.email if report.user else "Anonymous"}. Action required.',
                link=f'/reports/admin/report/{report.report_id}/',
                report=report
            )
            
            # Send email to admin
            try:
                send_mail(
                    subject=f'[GridWatch Admin] New Report: {report.report_id}',
                    message=f"""
                    A new report has been submitted:
                    
                    Report ID: {report.report_id}
                    Type: {report.get_outage_type_display()}
                    Location: {report.location_text}
                    Reported By: {report.user.email if report.user else 'Anonymous'}
                    Contact: {report.contact_info or 'Not provided'}
                    
                    View and process this report:
                    {settings.SITE_URL}/reports/admin/report/{report.report_id}/
                    
                    ---
                    GridWatch Admin System
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Failed to send admin email notification: {e}")