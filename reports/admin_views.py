# reports/admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from .models import OutageReport, ReportUpdate, Notification
from .forms import AdminReportUpdateForm
from .notification_service import NotificationService
from django.contrib.auth import get_user_model
from .geocoding_utils import geocode_location

import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard with analytics and report list"""
    # Statistics
    total_reports = OutageReport.objects.count()
    pending_reports = OutageReport.objects.filter(status='pending').count()
    in_progress_reports = OutageReport.objects.filter(status='in_progress').count()
    resolved_reports = OutageReport.objects.filter(status='resolved').count()
    
    # Reports by type - ensure we always have data
    reports_by_type = OutageReport.objects.values('outage_type').annotate(count=Count('id'))
    
    # If no reports by type, provide default empty data
    if not reports_by_type:
        reports_by_type = []
    
    # Recent reports - get latest 5 reports
    recent_reports = OutageReport.objects.all().order_by('-reported_at')[:5]
    
    context = {
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'in_progress_reports': in_progress_reports,
        'resolved_reports': resolved_reports,
        'reports_by_type': reports_by_type,
        'recent_reports': recent_reports,
    }
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def admin_reports_list(request):
    """Paginated list of all reports for admin (10 per page)"""
    reports = OutageReport.objects.select_related('user').all()
    
    # Filtering
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    search_query = request.GET.get('search')
    
    if status_filter:
        reports = reports.filter(status=status_filter)
    if type_filter:
        reports = reports.filter(outage_type=type_filter)
    if search_query:
        reports = reports.filter(
            Q(report_id__icontains=search_query) |
            Q(location_text__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination - 10 per page
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'reports': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'search_query': search_query,
        'total_count': paginator.count,
    }
    return render(request, 'admin/reports_list.html', context)


# reports/admin_views.py - Complete updated admin_report_detail function

from .geocoding_utils import geocode_location  # Add this import at the top

@staff_member_required
def admin_report_detail(request, report_id):
    """View and update individual report with auto-geocoding"""
    report = get_object_or_404(OutageReport, report_id=report_id)
    
    if request.method == 'POST':
        # Capture OLD status BEFORE any changes
        old_status = report.status
        old_location = report.location_text  # Capture old location for geocoding check
        
        print(f"\n{'='*50}")
        print(f"BEFORE FORM: Old Status = {old_status}")
        print(f"BEFORE FORM: Old Location = {old_location}")
        
        form = AdminReportUpdateForm(request.POST, instance=report)
        
        if form.is_valid():
            # Get the NEW status from cleaned_data
            new_status = form.cleaned_data.get('status')
            new_location = form.cleaned_data.get('location_text')
            
            print(f"AFTER FORM: New Status from form = {new_status}")
            print(f"AFTER FORM: New Location from form = {new_location}")
            
            # Save the form but don't commit yet
            report = form.save(commit=False)
            
            # Handle verification
            if new_status == 'verified' and old_status != 'verified':
                report.verified_at = timezone.now()
                report.verified_by = request.user
            
            # Handle resolution
            if new_status == 'resolved' and old_status != 'resolved':
                report.resolved_at = timezone.now()
            
            # Auto-geocode if location changed and coordinates are missing
            if old_location != new_location and new_location:
                print(f"Location changed, attempting to geocode: {new_location}")
                lat, lng = geocode_location(new_location)
                if lat and lng:
                    report.latitude = lat
                    report.longitude = lng
                    print(f"Successfully geocoded: {new_location} -> ({lat}, {lng})")
                else:
                    print(f"Could not geocode: {new_location}")
                    # Keep existing coordinates or set to None
                    if not (report.latitude and report.longitude):
                        report.latitude = None
                        report.longitude = None
            
            report.save()
            
            # Create update log
            ReportUpdate.objects.create(
                report=report,
                status=report.status,
                note=form.cleaned_data.get('admin_notes', ''),
                created_by=request.user
            )
            
            print(f"Old Status: {old_status}")
            print(f"New Status: {report.status}")
            print(f"Status Changed: {old_status != report.status}")
            print(f"Has Coordinates: {bool(report.latitude and report.longitude)}")
            
            # Send notifications ONLY if status actually changed
            if old_status != report.status and report.user and report.user.email:
                print(f"Sending notification to {report.user.email}...")
                
                # Send status update email and in-app notification
                NotificationService.send_status_update_email(
                    report, 
                    old_status, 
                    report.status,
                    form.cleaned_data.get('admin_notes')
                )
                
                # If resolved, send resolution notice
                if report.status == 'resolved':
                    NotificationService.send_resolution_notice(report)
                    
            elif old_status == report.status:
                print("Status did not change - no notification sent")
            else:
                print("No user associated with report - no notification sent")
            
            messages.success(request, f'Report {report.report_id} updated successfully')
            return redirect('reports:admin_report_detail', report_id=report.report_id)
        else:
            print(f"Form errors: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminReportUpdateForm(instance=report)
    
    # Get status history
    updates = report.updates.all().order_by('-created_at')
    
    context = {
        'report': report,
        'form': form,
        'updates': updates,
    }
    return render(request, 'admin/report_detail.html', context)


@staff_member_required
def admin_bulk_update(request):
    """Bulk update multiple reports at once"""
    if request.method == 'POST':
        report_ids = request.POST.getlist('report_ids')
        new_status = request.POST.get('status')
        
        if report_ids and new_status:
            reports = OutageReport.objects.filter(report_id__in=report_ids)
            count = 0
            
            for report in reports:
                old_status = report.status
                report.status = new_status
                
                if new_status == 'resolved' and old_status != 'resolved':
                    report.resolved_at = timezone.now()
                
                report.save()
                
                ReportUpdate.objects.create(
                    report=report,
                    status=new_status,
                    note=f'Bulk update by admin',
                    created_by=request.user
                )
                
                if report.user and old_status != new_status:
                    # Send notification to user
                    NotificationService.send_status_update_email(
                        report, 
                        old_status, 
                        new_status,
                        'Bulk status update'
                    )
                
                count += 1
            
            messages.success(request, f'Updated {count} reports to {new_status}')
    
    return redirect('reports:admin_reports_list')


@staff_member_required
def admin_notifications(request):
    """View all admin notifications (system alerts)"""
    return render(request, 'admin/notifications.html')


def api_report_status(request, report_id):
    """API endpoint for real-time status checking"""
    try:
        report = OutageReport.objects.get(report_id=report_id)
        
        data = {
            'status': report.status,
            'status_display': report.get_status_display(),
            'status_color': report.get_status_color(),
            'status_icon': report.get_status_icon(),
            'updated_at': report.updated_at.isoformat(),
            'estimated_restoration': report.estimated_restoration_time.isoformat() if report.estimated_restoration_time else None,
            'resolution_notes': report.resolution_notes,
        }
        
        return JsonResponse({'success': True, 'report': data})
    except OutageReport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'}, status=404)


def api_user_notifications(request):
    """API endpoint for user notifications (AJAX polling)"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')
    
    data = {
        'count': notifications.count(),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'created_at': n.created_at.isoformat(),
                'report_id': n.report.report_id if n.report else None,
            } for n in notifications[:10]
        ]
    }
    
    return JsonResponse({'success': True, 'data': data})


@staff_member_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'success': True})


@staff_member_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    return JsonResponse({'success': True})


@staff_member_required
def api_admin_notifications(request):
    """API endpoint for admin system notifications"""
    from django.http import JsonResponse
    
    # For now, return empty array or sample data
    notifications = [
        {
            'id': 1,
            'title': 'System Status: All Systems Operational',
            'message': 'GridWatch is running normally with no reported issues.',
            'type': 'info',
            'priority': 'normal',
            'is_read': False,
            'created_at': '2024-01-15T10:30:00'
        }
    ]
    
    return JsonResponse({
        'success': True,
        'notifications': notifications,
        'total': len(notifications),
        'unread': len([n for n in notifications if not n['is_read']])
    })