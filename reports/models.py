# reports/mdoels.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class OutageReport(models.Model):
    # Outage Types
    OUTAGE_TYPES = [
        ('electricity', '⚡ Electricity'),
        ('water', '💧 Water Supply'),
        ('network', '📡 Network/Telecom'),
    ]
    
    # Status Choices
    STATUS_CHOICES = [
        ('pending', '📝 Pending Verification'),
        ('verified', '✅ Verified'),
        ('in_progress', '🔧 In Progress'),
        ('resolved', '✔️ Resolved'),
        ('rejected', '❌ Rejected'),
    ]
    
    # Basic Info
    report_id = models.CharField(max_length=20, unique=True, editable=False)
    outage_type = models.CharField(max_length=20, choices=OUTAGE_TYPES)
    
    # Location
    location_text = models.CharField(max_length=200, help_text="Village or community name")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Report Details
    description = models.TextField(help_text="Describe the outage issue")
    contact_info = models.CharField(max_length=100, blank=True, null=True, help_text="Phone number or email (optional)")
    
    # Media
    photo = models.ImageField(upload_to='outage_photos/%Y/%m/%d/', blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admin")
    resolution_notes = models.TextField(blank=True, help_text="Notes when resolved")
    
    # User Association
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    is_anonymous = models.BooleanField(default=False)
    anonymous_name = models.CharField(max_length=100, blank=True, help_text="Optional name for anonymous reports")
    estimated_restoration_time = models.DateTimeField(null=True, blank=True, help_text="Estimated time when service will be restored")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_reports')
    assigned_to = models.CharField(max_length=100, blank=True, help_text="Team or person assigned to fix")
    
    # Timestamps
    reported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    
    class Meta:
        ordering = ['-reported_at']
        indexes = [
            models.Index(fields=['status', '-reported_at']),
            models.Index(fields=['outage_type']),
            models.Index(fields=['location_text']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.report_id:
            # Generate unique report ID: GW-20241215-001 format
            date_str = timezone.now().strftime('%Y%m%d')
            last_report = OutageReport.objects.filter(
                report_id__startswith=f'GW-{date_str}'
            ).order_by('-report_id').first()
            
            if last_report:
                last_num = int(last_report.report_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.report_id = f'GW-{date_str}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.report_id} - {self.get_outage_type_display()} in {self.location_text}"
    
    def get_status_icon(self):
        icons = {
            'pending': 'fa-clock',
            'verified': 'fa-check-circle',
            'in_progress': 'fa-tools',
            'resolved': 'fa-check-double',
            'rejected': 'fa-times-circle',
        }
        return icons.get(self.status, 'fa-question-circle')
    
    def get_status_color(self):
        colors = {
            'pending': '#F59E0B',
            'verified': '#3B82F6',
            'in_progress': '#8B5CF6',
            'resolved': '#10B981',
            'rejected': '#EF4444',
        }
        return colors.get(self.status, '#6B7280')
    
    def get_status_history(self):
        """Get formatted status history for timeline"""
        return self.updates.all()
    
    def can_user_edit(self, user):
        """Check if user can edit this report"""
        if user.is_admin:
            return True
        return self.user == user and self.status == 'pending'
    
    @property
    def time_to_resolution(self):
        if self.resolved_at and self.reported_at:
            delta = self.resolved_at - self.reported_at
            return delta.total_seconds() / 3600  # Hours
        return None


class ReportUpdate(models.Model):
    """Track status changes and updates on reports"""
    report = models.ForeignKey(OutageReport, on_delete=models.CASCADE, related_name='updates')
    status = models.CharField(max_length=20, choices=OutageReport.STATUS_CHOICES)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report.report_id} - {self.get_status_display()} at {self.created_at}"


class Notification(models.Model):
    """Unified In-app notifications for users"""
    NOTIFICATION_TYPES = [
        ('welcome', 'Welcome'),
        ('report_submitted', 'Report Submitted'),
        ('status_update', 'Status Update'),
        ('report_verified', 'Report Verified'),
        ('report_resolved', 'Report Resolved'),
        ('admin_message', 'Admin Message'),
        ('system_alert', 'System Alert'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    report = models.ForeignKey(OutageReport, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"


class PushSubscription(models.Model):
    """Store Web Push API subscriptions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.created_at}"


class EmailLog(models.Model):
    """Track email notifications sent"""
    recipient = models.EmailField()
    subject = models.CharField(max_length=500)
    notification_type = models.CharField(max_length=50)
    report = models.ForeignKey(OutageReport, on_delete=models.SET_NULL, null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='sent')  # sent, failed, bounced
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient} at {self.sent_at}"
    
    
class ReportReaction(models.Model):
    """User reactions/upvotes on reports"""
    REACTION_TYPES = [
        ('urgent', '🚨 Urgent'),
        ('helpful', '👍 Helpful'),
        ('confirm', '✅ Confirmed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_reactions')
    report = models.ForeignKey(OutageReport, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'report')  # One reaction per user per report
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.reaction_type} on {self.report.report_id}"


class ReportComment(models.Model):
    """Comments on reports"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_comments')
    report = models.ForeignKey(OutageReport, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.user.email} on {self.report.report_id}"
    

class SavedPost(models.Model):
    """Model for users to save posts they want to keep track of"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_posts')
    report = models.ForeignKey(OutageReport, on_delete=models.CASCADE, related_name='saved_by_users')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'report')  # Prevent duplicate saves
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} saved {self.report.report_id}"