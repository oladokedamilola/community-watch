# accounts/views/general_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..forms import UserProfileForm
from ..models import Profile


@login_required
def profile_view(request):
    """View and edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def dashboard_view(request):
    """Redirect to appropriate dashboard based on user role"""
    if request.user.is_admin:
        return redirect('reports:admin_dashboard')
    else:
        return redirect('reports:community_dashboard')


@login_required
def upload_profile_picture(request):
    """AJAX endpoint for profile picture upload"""
    import json
    from django.http import JsonResponse
    
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        try:
            profile, created = Profile.objects.get_or_create(user=request.user)
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            
            return JsonResponse({
                'success': True,
                'image_url': profile.get_profile_picture_url()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'No file provided'})