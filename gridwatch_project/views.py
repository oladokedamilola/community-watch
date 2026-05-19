from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.core.management import call_command
from io import StringIO
import traceback

User = get_user_model()

def custom_404_view(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_500_view(request):
    return render(request, 'errors/500.html', status=500)

def custom_403_view(request, exception):
    return render(request, 'errors/403.html', status=403)

def custom_400_view(request, exception):
    return render(request, 'errors/400.html', status=400)

def csrf_failure_view(request, reason=""):
    return render(request, 'errors/403_csrf.html', {'reason': reason}, status=403)


@csrf_exempt
def run_migrations(request):
    """Run migrations via browser (temporary - remove after deploy)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)
    
    output = StringIO()
    errors = StringIO()
    
    try:
        call_command('migrate', stdout=output, stderr=errors)
        return JsonResponse({
            'success': True,
            'output': output.getvalue(),
            'errors': errors.getvalue()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@csrf_exempt
def create_superuser(request):
    """Create superuser via browser (temporary - remove after deploy)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)
    
    try:
        email = request.POST.get('email', 'admin@gridwatch.com')
        password = request.POST.get('password', 'Admin@123456')
        first_name = request.POST.get('first_name', 'Admin')
        last_name = request.POST.get('last_name', 'User')
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'User already exists'}, status=400)
        
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_admin=True,
            is_staff=True,
            is_superuser=True
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Superuser created: {email}',
            'password': password
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def collect_static(request):
    """Collect static files via browser (temporary - remove after deploy)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)
    
    output = StringIO()
    errors = StringIO()
    
    try:
        call_command('collectstatic', '--noinput', stdout=output, stderr=errors)
        return JsonResponse({
            'success': True,
            'output': output.getvalue(),
            'errors': errors.getvalue()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)