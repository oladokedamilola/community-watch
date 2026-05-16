# reports/notification_views.py
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Notification, PushSubscription
from .notification_service import NotificationService
import json


@login_required
def notification_history_view(request):
    """View for notification history page"""
    return render(request, 'reports/notification_history.html')


@login_required
@require_http_methods(['GET'])
def api_get_notifications(request):
    """Get unread notifications for current user"""
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:50]
    
    data = {
        'count': notifications.count(),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'link': n.link,
                'type': n.notification_type,
                'created_at': n.created_at.isoformat(),
                'created_at_display': n.created_at.strftime('%b %d, %I:%M %p'),
                'report_id': n.report.report_id if n.report else None,
            } for n in notifications
        ]
    }
    
    return JsonResponse({'success': True, 'data': data})


@login_required
@require_http_methods(['GET'])
def api_notification_count(request):
    """Get unread notification count for badge"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'success': True, 'count': count})


@login_required
@require_http_methods(['POST'])
def api_mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
def api_mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['DELETE'])
def api_delete_notification(request, notification_id):
    """Delete a notification"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
def api_subscribe_push(request):
    """Subscribe to web push notifications"""
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        p256dh = data.get('keys', {}).get('p256dh')
        auth = data.get('keys', {}).get('auth')
        
        if not all([endpoint, p256dh, auth]):
            return JsonResponse({'success': False, 'error': 'Missing subscription data'}, status=400)
        
        # Save or update subscription
        subscription, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'is_active': True
            }
        )
        
        return JsonResponse({'success': True, 'created': created})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_unsubscribe_push(request):
    """Unsubscribe from web push notifications"""
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def api_vapid_public_key(request):
    """Return VAPID public key for web push"""
    from django.conf import settings
    return JsonResponse({
        'success': True,
        'public_key': settings.WEBPUSH_SETTINGS.get('VAPID_PUBLIC_KEY', '')
    })


@login_required
@require_http_methods(['GET'])
def api_notification_history(request):
    """Get paginated notification history for user (10 per page)"""
    filter_type = request.GET.get('filter', 'all')
    page = request.GET.get('page', 1)
    
    # Base queryset
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Apply filter
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Pagination - 10 per page
    paginator = Paginator(notifications, 10)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Get counts for stats
    total_count = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    data = {
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'link': n.link,
                'type': n.notification_type,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'created_at_display': n.created_at.strftime('%b %d, %Y at %I:%M %p'),
                'report_id': n.report.report_id if n.report else None,
            } for n in page_obj
        ],
        'stats': {
            'total': total_count,
            'unread': unread_count,
        },
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'total_count': paginator.count,
        }
    }
    
    return JsonResponse({'success': True, 'data': data})


@login_required
@require_http_methods(['DELETE'])
def api_delete_all_read(request):
    """Delete all read notifications"""
    Notification.objects.filter(user=request.user, is_read=True).delete()
    return JsonResponse({'success': True})