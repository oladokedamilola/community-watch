# reports/urls.py
from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views
from . import admin_views
from . import map_views
from . import notification_views
from . import analytics_views
from . import feed_views


app_name = 'reports'

urlpatterns = [
    # Legacy Dashboard routes
    path('admin/redirect/', views.admin_dashboard_redirect, name='admin_dashboard_redirect'),
    
    # Public Feed
    path('feed/', feed_views.public_feed_view, name='public_feed'),
    path('api/load-more/', feed_views.load_more_posts, name='load_more_posts'),
    
    # Reaction and Comment APIs
    path('api/reaction/<int:report_id>/', feed_views.add_reaction, name='add_reaction'),
    path('api/comment/<int:report_id>/', feed_views.add_comment, name='add_comment'),
    path('api/comments/<int:report_id>/', feed_views.get_comments, name='get_comments'),
    path('api/comment/<int:comment_id>/delete/', feed_views.delete_comment, name='delete_comment'),
    path('api/reactions/counts/<int:report_id>/', feed_views.get_reaction_counts, name='get_reaction_counts'),
    
    
    # Saved Posts URLs
    path('api/save-post/<int:report_id>/', feed_views.save_post, name='save_post'),
    path('api/saved-status/<int:report_id>/', feed_views.get_saved_status, name='get_saved_status'),
    path('saved/', feed_views.saved_posts_view, name='saved_posts'),

    # User routes
    path('dashboard/', login_required(views.my_reports_view), name='dashboard'),
    path('report/', login_required(views.report_form_view), name='report_form'),
    path('my-reports/', login_required(views.my_reports_view), name='my_reports'),
    path('track/<str:report_id>/', views.track_report_view, name='track_report'),
    
    # Admin routes
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/reports/', admin_views.admin_reports_list, name='admin_reports_list'),
    path('admin/report/<str:report_id>/', admin_views.admin_report_detail, name='admin_report_detail'),
    path('admin/bulk-update/', admin_views.admin_bulk_update, name='admin_bulk_update'),
    
    
    # Analytics URLs
    path('admin/analytics/', analytics_views.analytics_dashboard, name='analytics_dashboard'),
    path('api/analytics/overview/', analytics_views.api_analytics_overview, name='api_analytics_overview'),
    path('api/analytics/trends/', analytics_views.api_analytics_trends, name='api_analytics_trends'),
    path('api/analytics/response-time/', analytics_views.api_analytics_response_time, name='api_analytics_response_time'),
    path('api/analytics/performance/', analytics_views.api_analytics_performance, name='api_analytics_performance'),
    path('api/analytics/export/csv/', analytics_views.api_analytics_export_csv, name='api_analytics_export_csv'),
    path('api/analytics/export/excel/', analytics_views.api_analytics_export_excel, name='api_analytics_export_excel'),
    path('api/analytics/export/pdf/', analytics_views.api_analytics_summary_pdf, name='api_analytics_summary_pdf'),
    path('api/analytics/heatmap/', analytics_views.api_analytics_heatmap_data, name='api_analytics_heatmap'),
    
    # Map views
    path('map/', map_views.outage_map_view, name='outage_map'),
    path('api/outages/geojson/', map_views.api_outage_geojson, name='api_outage_geojson'),
    path('api/outages/heatmap/', map_views.api_outage_heatmap, name='api_outage_heatmap'),
    path('api/outages/nearby/', map_views.api_nearby_outages, name='api_nearby_outages'),
    path('api/search-location/', map_views.api_search_location, name='api_search_location'),
    path('api/reverse-geocode/', map_views.api_reverse_geocode, name='api_reverse_geocode'),
    
    # Notifications
    path('notifications/', notification_views.notification_history_view, name='notification_history'),
     # Notification API endpoints
    path('api/notifications/', notification_views.api_get_notifications, name='api_get_notifications'),
    path('api/notifications/count/', notification_views.api_notification_count, name='api_notification_count'),
    path('api/notifications/mark-read/<int:notification_id>/', notification_views.api_mark_notification_read, name='api_mark_notification_read'),
    path('api/notifications/mark-all-read/', notification_views.api_mark_all_read, name='api_mark_all_read'),
    path('api/notifications/delete/<int:notification_id>/', notification_views.api_delete_notification, name='api_delete_notification'),
    path('api/push/subscribe/', notification_views.api_subscribe_push, name='api_subscribe_push'),
    path('api/push/unsubscribe/', notification_views.api_unsubscribe_push, name='api_unsubscribe_push'),
    path('api/push/vapid-key/', notification_views.api_vapid_public_key, name='api_vapid_public_key'),
    path('api/notifications/history/', notification_views.api_notification_history, name='api_notification_history'), 
    path('api/admin/notifications/', admin_views.api_admin_notifications, name='api_admin_notifications'),
    
    # API endpoints
    path('api/submit/', views.submit_report_ajax, name='submit_report_ajax'),
    path('api/report/<str:report_id>/status/', admin_views.api_report_status, name='api_report_status'),
    path('api/notifications/', login_required(admin_views.api_user_notifications), name='api_user_notifications'),
    path('api/notifications/mark-read/<int:notification_id>/', login_required(admin_views.mark_notification_read), name='mark_notification_read'),
    path('api/notifications/mark-all-read/', login_required(admin_views.mark_all_notifications_read), name='mark_all_notifications_read'),
]