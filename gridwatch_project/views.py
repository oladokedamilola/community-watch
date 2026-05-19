from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError

def custom_404_view(request, exception):
    """Custom 404 page not found handler"""
    return render(request, 'errors/404.html', status=404)

def custom_500_view(request):
    """Custom 500 server error handler"""
    return render(request, 'errors/500.html', status=500)

def custom_403_view(request, exception):
    """Custom 403 permission denied handler"""
    return render(request, 'errors/403.html', status=403)

def custom_400_view(request, exception):
    """Custom 400 bad request handler"""
    return render(request, 'errors/400.html', status=400)

def csrf_failure_view(request, reason=""):
    """Custom CSRF failure handler"""
    return render(request, 'errors/403_csrf.html', {'reason': reason}, status=403)