# reports/feed_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Count, Q
from .models import OutageReport, ReportReaction, ReportComment, SavedPost
from .notification_service import NotificationService
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def public_feed_view(request):
    """Public feed showing all reports from all users"""
    # Get filter parameters
    outage_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    sort_by = request.GET.get('sort', 'latest')
    
    # Base queryset - show all non-rejected reports
    reports = OutageReport.objects.exclude(status='rejected')
    
    # Apply filters
    if outage_type != 'all':
        reports = reports.filter(outage_type=outage_type)
    
    if status != 'all':
        reports = reports.filter(status=status)
    
    # Apply sorting
    if sort_by == 'latest':
        reports = reports.order_by('-reported_at')
    elif sort_by == 'oldest':
        reports = reports.order_by('reported_at')
    elif sort_by == 'most_urgent':
        reports = reports.annotate(
            urgent_count=Count('reactions', filter=Q(reactions__reaction_type='urgent'))
        ).order_by('-urgent_count', '-reported_at')
    elif sort_by == 'most_helpful':
        reports = reports.annotate(
            helpful_count=Count('reactions', filter=Q(reactions__reaction_type='helpful'))
        ).order_by('-helpful_count', '-reported_at')
    elif sort_by == 'most_commented':
        reports = reports.annotate(
            comment_count=Count('comments')
        ).order_by('-comment_count', '-reported_at')
    
    # Pagination - 15 posts per page for initial load
    paginator = Paginator(reports, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get user's reactions for the displayed reports
    user_reactions = {}
    for report in page_obj:
        try:
            reaction = ReportReaction.objects.filter(user=request.user, report=report).first()
            if reaction:
                user_reactions[report.id] = reaction.reaction_type
        except:
            pass
    
    # Get saved status for reports
    saved_reports = SavedPost.objects.filter(user=request.user).values_list('report_id', flat=True)
    
    context = {
        'reports': page_obj,
        'user_reactions': user_reactions,
        'saved_reports': saved_reports,
        'current_type': outage_type,
        'current_status': status,
        'current_sort': sort_by,
        'has_next': page_obj.has_next(),  
    }
    return render(request, 'reports/public_feed.html', context)


@login_required
@require_http_methods(['POST'])
def add_reaction(request, report_id):
    """Add or remove a reaction from a report"""
    try:
        data = json.loads(request.body)
        reaction_type = data.get('reaction_type')
        
        report = get_object_or_404(OutageReport, id=report_id)
        
        # Check if user already has a reaction on this report
        existing_reaction = ReportReaction.objects.filter(
            user=request.user, 
            report=report
        ).first()
        
        if existing_reaction:
            # If same reaction, remove it (toggle off)
            if existing_reaction.reaction_type == reaction_type:
                existing_reaction.delete()
                # Get updated counts
                urgent_count = ReportReaction.objects.filter(report=report, reaction_type='urgent').count()
                helpful_count = ReportReaction.objects.filter(report=report, reaction_type='helpful').count()
                
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'reaction_type': reaction_type,
                    'count': urgent_count if reaction_type == 'urgent' else helpful_count,
                    'urgent_count': urgent_count,
                    'helpful_count': helpful_count
                })
            else:
                # Update to different reaction
                existing_reaction.reaction_type = reaction_type
                existing_reaction.save()
                
                # Get updated counts
                urgent_count = ReportReaction.objects.filter(report=report, reaction_type='urgent').count()
                helpful_count = ReportReaction.objects.filter(report=report, reaction_type='helpful').count()
                
                # Send notification to report owner
                if report.user != request.user and report.user:
                    NotificationService.create_inapp_notification(
                        user=report.user,
                        notification_type='system_alert',
                        title=f'Reaction on your report',
                        message=f'{request.user.get_full_name() or request.user.email} reacted "{reaction_type}" to your report {report.report_id}',
                        link=f'/reports/track/{report.report_id}/',
                        report=report
                    )
                
                return JsonResponse({
                    'success': True,
                    'action': 'updated',
                    'reaction_type': reaction_type,
                    'count': urgent_count if reaction_type == 'urgent' else helpful_count,
                    'urgent_count': urgent_count,
                    'helpful_count': helpful_count
                })
        else:
            # Add new reaction
            reaction = ReportReaction.objects.create(
                user=request.user,
                report=report,
                reaction_type=reaction_type
            )
            
            # Get updated counts
            urgent_count = ReportReaction.objects.filter(report=report, reaction_type='urgent').count()
            helpful_count = ReportReaction.objects.filter(report=report, reaction_type='helpful').count()
            
            # Send notification to report owner
            if report.user != request.user and report.user:
                NotificationService.create_inapp_notification(
                    user=report.user,
                    notification_type='system_alert',
                    title=f'New reaction on your report',
                    message=f'{request.user.get_full_name() or request.user.email} marked your report as "{reaction_type}"',
                    link=f'/reports/track/{report.report_id}/',
                    report=report
                )
            
            return JsonResponse({
                'success': True,
                'action': 'added',
                'reaction_type': reaction_type,
                'count': urgent_count if reaction_type == 'urgent' else helpful_count,
                'urgent_count': urgent_count,
                'helpful_count': helpful_count
            })
            
    except Exception as e:
        logger.error(f"Error in add_reaction: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(['POST'])
def add_comment(request, report_id):
    """Add a comment to a report"""
    try:
        data = json.loads(request.body)
        comment_text = data.get('comment', '').strip()
        
        if not comment_text:
            return JsonResponse({'success': False, 'error': 'Comment cannot be empty'}, status=400)
        
        if len(comment_text) > 500:
            return JsonResponse({'success': False, 'error': 'Comment too long (max 500 characters)'}, status=400)
        
        report = get_object_or_404(OutageReport, id=report_id)
        
        comment = ReportComment.objects.create(
            user=request.user,
            report=report,
            comment=comment_text
        )
        
        # Get updated comment count
        comment_count = ReportComment.objects.filter(report=report).count()
        
        # Send notification to report owner
        if report.user != request.user and report.user:
            NotificationService.create_inapp_notification(
                user=report.user,
                notification_type='system_alert',
                title=f'New comment on your report',
                message=f'{request.user.get_full_name() or request.user.email} commented on {report.report_id}: "{comment_text[:50]}{"..." if len(comment_text) > 50 else ""}"',
                link=f'/reports/track/{report.report_id}/',
                report=report
            )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'user_name': comment.user.get_full_name() or comment.user.email,
                'comment': comment.comment,
                'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
                'created_at_relative': get_time_ago(comment.created_at)
            },
            'comment_count': comment_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)



@login_required
@require_http_methods(['GET'])
def get_reaction_counts(request, report_id):
    """Get reaction counts for a report"""
    try:
        report = get_object_or_404(OutageReport, id=report_id)
        
        # Count specific reaction types
        urgent_count = ReportReaction.objects.filter(report=report, reaction_type='urgent').count()
        helpful_count = ReportReaction.objects.filter(report=report, reaction_type='helpful').count()
        
        # Get user's current reaction
        user_reaction = None
        try:
            reaction = ReportReaction.objects.filter(user=request.user, report=report).first()
            if reaction:
                user_reaction = reaction.reaction_type
        except Exception as e:
            logger.error(f"Error getting user reaction: {e}")
        
        return JsonResponse({
            'success': True,
            'urgent_count': urgent_count,
            'helpful_count': helpful_count,
            'user_reaction': user_reaction
        })
        
    except OutageReport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in get_reaction_counts: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def get_comments(request, report_id):
    """Get all comments for a report"""
    try:
        report = get_object_or_404(OutageReport, id=report_id)
        comments = report.comments.all()
        
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'user_name': comment.user.get_full_name() or comment.user.email,
                'user_avatar': comment.user.profile.get_profile_picture_url() if hasattr(comment.user, 'profile') else None,
                'comment': comment.comment,
                'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
                'created_at_relative': get_time_ago(comment.created_at),
                'is_owner': comment.user == request.user
            })
        
        return JsonResponse({
            'success': True,
            'comments': comments_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(['DELETE'])
def delete_comment(request, comment_id):
    """Delete a comment (only owner or admin)"""
    try:
        comment = get_object_or_404(ReportComment, id=comment_id)
        
        if comment.user != request.user and not request.user.is_admin:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        report_id = comment.report.id
        comment.delete()
        
        comment_count = ReportComment.objects.filter(report_id=report_id).count()
        
        return JsonResponse({
            'success': True,
            'comment_count': comment_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def get_time_ago(dt):
    """Get human-readable time ago string"""
    from django.utils import timezone
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 7:
        return f"{diff.days // 7} weeks ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "Just now"
    
    
    
@login_required
@require_http_methods(['POST'])
def save_post(request, report_id):
    """Save or unsave a post"""
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'save' or 'unsave'
        
        report = get_object_or_404(OutageReport, id=report_id)
        
        if action == 'save':
            saved_post, created = SavedPost.objects.get_or_create(
                user=request.user,
                report=report
            )
            is_saved = True
        else:
            SavedPost.objects.filter(user=request.user, report=report).delete()
            is_saved = False
        
        # Get total saves count
        saves_count = SavedPost.objects.filter(report=report).count()
        
        return JsonResponse({
            'success': True,
            'is_saved': is_saved,
            'saves_count': saves_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def get_saved_status(request, report_id):
    """Get save status for a report"""
    try:
        report = get_object_or_404(OutageReport, id=report_id)
        is_saved = SavedPost.objects.filter(user=request.user, report=report).exists()
        saves_count = SavedPost.objects.filter(report=report).count()
        
        return JsonResponse({
            'success': True,
            'is_saved': is_saved,
            'saves_count': saves_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def saved_posts_view(request):
    """View for user's saved posts"""
    saved_posts = SavedPost.objects.filter(user=request.user).select_related('report')
    
    # Get filter parameters
    outage_type = request.GET.get('type', 'all')
    sort_by = request.GET.get('sort', 'latest')
    
    reports = [saved.report for saved in saved_posts]
    
    # Apply filters
    if outage_type != 'all':
        reports = [r for r in reports if r.outage_type == outage_type]
    
    # Apply sorting
    if sort_by == 'latest':
        reports = sorted(reports, key=lambda x: x.reported_at, reverse=True)
    elif sort_by == 'oldest':
        reports = sorted(reports, key=lambda x: x.reported_at)
    elif sort_by == 'most_urgent':
        reports = sorted(reports, key=lambda x: x.reactions.filter(reaction_type='urgent').count(), reverse=True)
    
    # Get user's reactions for these reports
    user_reactions = {}
    for report in reports:
        try:
            reaction = ReportReaction.objects.filter(user=request.user, report=report).first()
            if reaction:
                user_reactions[report.id] = reaction.reaction_type
        except:
            pass
    
    context = {
        'reports': reports,
        'user_reactions': user_reactions,
        'current_type': outage_type,
        'current_sort': sort_by,
        'is_saved_page': True,
    }
    return render(request, 'reports/saved_posts.html', context)



@login_required
def load_more_posts(request):
    """AJAX endpoint to load more posts for infinite scroll"""
    # Get filter parameters
    outage_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    sort_by = request.GET.get('sort', 'latest')
    page = int(request.GET.get('page', 2))  # Start from page 2
    
    # Base queryset - show all non-rejected reports
    reports = OutageReport.objects.exclude(status='rejected')
    
    # Apply filters
    if outage_type != 'all':
        reports = reports.filter(outage_type=outage_type)
    
    if status != 'all':
        reports = reports.filter(status=status)
    
    # Apply sorting
    if sort_by == 'latest':
        reports = reports.order_by('-reported_at')
    elif sort_by == 'oldest':
        reports = reports.order_by('reported_at')
    elif sort_by == 'most_urgent':
        reports = reports.annotate(
            urgent_count=Count('reactions', filter=Q(reactions__reaction_type='urgent'))
        ).order_by('-urgent_count', '-reported_at')
    elif sort_by == 'most_helpful':
        reports = reports.annotate(
            helpful_count=Count('reactions', filter=Q(reactions__reaction_type='helpful'))
        ).order_by('-helpful_count', '-reported_at')
    elif sort_by == 'most_commented':
        reports = reports.annotate(
            comment_count=Count('comments')
        ).order_by('-comment_count', '-reported_at')
    
    # Pagination - 15 posts per page
    paginator = Paginator(reports, 15)
    
    # Get the requested page
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        # Return empty response if page doesn't exist
        return HttpResponse('')
    
    # Get user's reactions for the reports
    user_reactions = {}
    for report in page_obj:
        try:
            reaction = ReportReaction.objects.filter(user=request.user, report=report).first()
            if reaction:
                user_reactions[report.id] = reaction.reaction_type
        except:
            pass
    
    # Get saved status for reports
    saved_reports = SavedPost.objects.filter(user=request.user).values_list('report_id', flat=True)
    
    context = {
        'reports': page_obj,
        'user_reactions': user_reactions,
        'saved_reports': saved_reports,
        'has_next': page_obj.has_next(),
        'current_page': page,
    }
    
    # Render only the posts partial template
    return render(request, 'reports/partials/feed_posts_partial.html', context)