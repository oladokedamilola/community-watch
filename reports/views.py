# reports/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from .models import OutageReport, ReportUpdate
from .forms import OutageReportForm
from .notification_service import NotificationService
import json
from .geocoding_utils import geocode_location
import logging
from django.db.models import Q
from .geocoding_utils import geocode_location


logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def community_dashboard(request):
    """Dashboard for regular community members"""
    # Get user's reports
    user_reports = OutageReport.objects.filter(user=request.user).order_by('-reported_at')[:5]
    
    # Statistics
    total_reports = OutageReport.objects.filter(user=request.user).count()
    pending_reports = OutageReport.objects.filter(user=request.user, status='pending').count()
    resolved_reports = OutageReport.objects.filter(user=request.user, status='resolved').count()
    
    # Get nearby reports based on user's village
    nearby_reports = []
    user_coordinates = None
    
    if request.user.village:
        # Try to geocode the user's village to get coordinates
        lat, lng = geocode_location(request.user.village)
        if lat and lng:
            user_coordinates = (lat, lng)
            
            # Get all reports with coordinates
            reports_with_coords = OutageReport.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False,
                status__in=['pending', 'verified', 'in_progress']
            ).exclude(user=request.user)
            
            # Calculate distance and sort by proximity
            nearby_reports = []
            for report in reports_with_coords:
                distance = calculate_distance(
                    lat, lng, 
                    float(report.latitude), float(report.longitude)
                )
                if distance <= 50:  # Within 50 km radius
                    nearby_reports.append((report, distance))
            
            # Sort by distance and get top 10
            nearby_reports.sort(key=lambda x: x[1])
            nearby_reports = [report for report, distance in nearby_reports[:10]]
    
    context = {
        'user_reports': user_reports,
        'nearby_reports': nearby_reports,
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'resolved_reports': resolved_reports,
        'user_coordinates': user_coordinates,
        'is_admin': False,
    }
    return render(request, 'reports/community_dashboard.html', context)


def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points in km (Haversine formula)"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in km
    
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return round(R * c, 2)

@login_required
def admin_dashboard_redirect(request):
    """Redirect admin to analytics dashboard"""
    if request.user.is_admin:
        return redirect('reports:analytics_dashboard')
    else:
        return redirect('reports:community_dashboard')


@login_required
def report_form_view(request):
    """Display the outage report form"""
    form = OutageReportForm()
    return render(request, 'reports/report_form.html', {'form': form})



@require_http_methods(['POST'])
def submit_report_ajax(request):
    """Handle AJAX form submission with auto-geocoding"""
    try:
        # Get form data
        outage_type = request.POST.get('outage_type')
        location_text = request.POST.get('location_text')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        description = request.POST.get('description')
        contact_info = request.POST.get('contact_info')
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        anonymous_name = request.POST.get('anonymous_name', '')
        
        # Validation
        if not outage_type or not location_text or not description:
            return JsonResponse({
                'success': False,
                'error': 'Please fill in all required fields'
            }, status=400)
        
        # If user didn't provide coordinates, try to geocode from location text
        if not latitude or not longitude:
            logger.info(f"Auto-geocoding location: {location_text}")
            lat, lng = geocode_location(location_text)
            if lat and lng:
                latitude = lat
                longitude = lng
                logger.info(f"Successfully geocoded: {location_text} -> ({lat}, {lng})")
        
        # Create report
        report = OutageReport.objects.create(
            outage_type=outage_type,
            location_text=location_text,
            latitude=latitude if latitude else None,
            longitude=longitude if longitude else None,
            description=description,
            contact_info=contact_info,
            is_anonymous=is_anonymous,
            anonymous_name=anonymous_name if is_anonymous else '',
            user=None if is_anonymous else request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Handle photo upload
        if request.FILES.get('photo'):
            report.photo = request.FILES['photo']
            report.save()
        
        # Create initial update log
        ReportUpdate.objects.create(
            report=report,
            status='pending',
            note='Report submitted',
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Send confirmation to user
        email_sent = False
        if not is_anonymous and request.user.is_authenticated:
            NotificationService.send_report_confirmation(report, request.user)
            email_sent = True
        elif contact_info and '@' in contact_info:
            temp_user = type('obj', (object,), {'email': contact_info, 'get_full_name': lambda: None})()
            NotificationService.send_report_confirmation(report, temp_user)
            email_sent = True
        
        # NOTIFY ALL ADMINS about new report
        NotificationService.notify_admins_new_report(report)
        
        # Send email directly as fallback
        recipient_email = None
        if not is_anonymous and request.user.is_authenticated:
            recipient_email = request.user.email
        elif contact_info and '@' in contact_info:
            recipient_email = contact_info
        
        if recipient_email and not email_sent:
            try:
                send_mail(
                    subject=f'GridWatch: Report Received - {report.report_id}',
                    message=f"""
                    Hello,
                    
                    Thank you for submitting an outage report to GridWatch. An administrator will review it shortly.
                    
                    Report ID: {report.report_id}
                    Outage Type: {report.get_outage_type_display()}
                    Location: {report.location_text}
                    
                    Track your report status here:
                    {settings.SITE_URL}/reports/track/{report.report_id}/
                    
                    Thank you for helping monitor outages in your community.
                    
                    — GridWatch Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=True,
                )
                email_sent = True
            except Exception as e:
                print(f"Email error: {e}")
        
        return JsonResponse({
            'success': True,
            'report_id': report.report_id,
            'message': 'Report submitted successfully! An administrator will review it shortly.',
            'tracking_url': f'/reports/track/{report.report_id}/',
            'email_sent': email_sent,
            'has_coordinates': bool(latitude and longitude)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def track_report_view(request, report_id):
    """Public tracking page for report status"""
    report = get_object_or_404(OutageReport, report_id=report_id)
    updates = report.updates.all()
    return render(request, 'reports/track_report.html', {
        'report': report,
        'updates': updates
    })


@login_required
def my_reports_view(request):
    """List reports submitted by logged-in user"""
    reports = OutageReport.objects.filter(user=request.user).order_by('-reported_at')
    
    # Pagination
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'reports/my_reports.html', {'reports': page_obj})