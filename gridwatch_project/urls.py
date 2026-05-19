from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
import reports.views as views
import reports.admin_views as admin_views
from . import views as error_views

# Dashboard redirect view based on user role
def dashboard_redirect(request):
    """Redirect users to their appropriate dashboard based on role"""
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin_dashboard')
        else:
            return redirect('community_dashboard')
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Direct dashboard URL - no nested app name
    path('dashboard/', login_required(dashboard_redirect), name='dashboard'),
    path('dashboard/community/', views.community_dashboard, name='community_dashboard'),
    path('dashboard/admin/', admin_views.admin_dashboard, name='admin_dashboard'),

    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('reports/', include('reports.urls')),
    path('', include('pwa.urls')),  # PWA URLs (manifest.json, service worker)
    
    
    # Temporary setup endpoints (remove after deploy)
    path('setup/migrate/', views.run_migrations, name='run_migrations'),
    path('setup/superuser/', views.create_superuser, name='create_superuser'),
    path('setup/static/', views.collect_static, name='collect_static'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# Custom error handlers
handler404 = error_views.custom_404_view
handler500 = error_views.custom_500_view
handler403 = error_views.custom_403_view
handler400 = error_views.custom_400_view