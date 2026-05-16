# reports/map_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from .models import OutageReport
import json
from datetime import datetime, timedelta

@login_required
def outage_map_view(request):
    """Main map view showing all outages"""
    return render(request, 'reports/map/outage_map.html')

# reports/map_views.py - Update the api_outage_geojson function

@require_http_methods(['GET'])
def api_outage_geojson(request):
    """API endpoint returning outage data as GeoJSON for mapping"""
    # Get filter parameters
    outage_type = request.GET.get('type')
    status = request.GET.get('status')
    days = request.GET.get('days', 30)
    
    # Base queryset
    reports = OutageReport.objects.all()
    
    # Apply filters
    if outage_type and outage_type != 'all':
        reports = reports.filter(outage_type=outage_type)
    
    if status and status != 'all':
        reports = reports.filter(status=status)
    
    # Filter by date range
    if days:
        cutoff_date = datetime.now() - timedelta(days=int(days))
        reports = reports.filter(reported_at__gte=cutoff_date)
    
    # Build GeoJSON - include all reports, but only show on map if they have coordinates
    features = []
    coordinates_missing = 0
    
    for report in reports:
        # Skip reports without coordinates - they won't appear on map
        if not report.latitude or not report.longitude:
            coordinates_missing += 1
            continue
        
        marker_colors = {
            'electricity': '#F59E0B',
            'water': '#3B82F6',
            'network': '#10B981',
        }
        
        status_icons = {
            'pending': 'clock',
            'verified': 'check-circle',
            'in_progress': 'tools',
            'resolved': 'check-double',
            'rejected': 'times-circle',
        }
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(report.longitude), float(report.latitude)]
            },
            'properties': {
                'id': report.report_id,
                'type': report.outage_type,
                'type_display': report.get_outage_type_display(),
                'status': report.status,
                'status_display': report.get_status_display(),
                'status_icon': status_icons.get(report.status, 'info-circle'),
                'location': report.location_text,
                'description': report.description[:150],
                'reported_at': report.reported_at.isoformat(),
                'reported_at_display': report.reported_at.strftime('%b %d, %Y - %I:%M %p'),
                'marker_color': marker_colors.get(report.outage_type, '#6B7280'),
                'estimated_restoration': report.estimated_restoration_time.isoformat() if report.estimated_restoration_time else None,
                'has_photo': bool(report.photo),
            }
        }
        features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'count': len(features),
            'total_reports': reports.count(),
            'coordinates_missing': coordinates_missing,
            'last_updated': datetime.now().isoformat()
        }
    }
    
    return JsonResponse(geojson)

@require_http_methods(['GET'])
def api_outage_heatmap(request):
    """API endpoint for heatmap data (aggregated by grid cells)"""
    # Get filter parameters
    outage_type = request.GET.get('type')
    status = request.GET.get('status')
    days = request.GET.get('days', 30)
    
    # Base queryset - active outages only
    reports = OutageReport.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Apply filters
    if outage_type and outage_type != 'all':
        reports = reports.filter(outage_type=outage_type)
    
    if status and status != 'all':
        reports = reports.filter(status=status)
    
    # Filter by date range
    if days:
        cutoff_date = datetime.now() - timedelta(days=int(days))
        reports = reports.filter(reported_at__gte=cutoff_date)
    
    # Build heatmap data
    heatmap_data = []
    for report in reports:
        # Round to 3 decimal places (~100m resolution)
        lat_rounded = round(float(report.latitude), 3)
        lng_rounded = round(float(report.longitude), 3)
        
        # Weight based on status and type
        weight = 1.0
        if report.status == 'pending':
            weight = 1.5
        elif report.status == 'verified':
            weight = 1.2
        elif report.status == 'resolved':
            weight = 0.3
        
        if report.outage_type == 'electricity':
            weight *= 1.2
        
        heatmap_data.append({
            'lat': lat_rounded,
            'lng': lng_rounded,
            'weight': weight,
            'type': report.outage_type
        })
    
    return JsonResponse({'success': True, 'data': heatmap_data})

@require_http_methods(['GET'])
def api_nearby_outages(request):
    """Find nearby outages within radius"""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius_km = request.GET.get('radius', 5)
    
    if not lat or not lng:
        return JsonResponse({'error': 'Missing coordinates'}, status=400)
    
    # Simple bounding box for nearby search
    # In production, use PostGIS for proper proximity search
    delta = float(radius_km) / 111.0  # Rough conversion: 1 deg lat ≈ 111 km
    
    reports = OutageReport.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        latitude__range=(float(lat) - delta, float(lat) + delta),
        longitude__range=(float(lng) - delta, float(lng) + delta),
        status__in=['pending', 'verified', 'in_progress']
    )[:20]
    
    data = []
    for report in reports:
        data.append({
            'id': report.report_id,
            'type': report.get_outage_type_display(),
            'status': report.get_status_display(),
            'location': report.location_text,
            'distance_km': calculate_distance(float(lat), float(lng), float(report.latitude), float(report.longitude)),
            'reported_at': report.reported_at.strftime('%b %d, %H:%M'),
        })
    
    return JsonResponse({'success': True, 'outages': data})

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

@require_http_methods(['GET'])
def api_search_location(request):
    """Search for location by name (using Nominatim)"""
    import requests
    
    query = request.GET.get('q')
    if not query:
        return JsonResponse({'error': 'Missing query'}, status=400)
    
    try:
        # Use OpenStreetMap Nominatim for geocoding
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'q': query,
                'format': 'json',
                'limit': 5,
                'countrycodes': 'ng,gh,ke,za,ci,sn,cm'  # Focus on African countries
            },
            headers={'User-Agent': 'GridWatch/1.0'}
        )
        
        if response.status_code == 200:
            results = response.json()
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'display_name': result.get('display_name', ''),
                    'lat': result.get('lat'),
                    'lon': result.get('lon'),
                    'type': result.get('type'),
                })
            return JsonResponse({'success': True, 'results': formatted_results})
        else:
            return JsonResponse({'success': False, 'error': 'Geocoding service error'}, status=500)
    
    except requests.RequestException as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['GET'])
def api_reverse_geocode(request):
    """Convert coordinates to location name"""
    import requests
    
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    
    if not lat or not lng:
        return JsonResponse({'error': 'Missing coordinates'}, status=400)
    
    try:
        response = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'zoom': 10
            },
            headers={'User-Agent': 'GridWatch/1.0'}
        )
        
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            
            # Build readable location name
            location_parts = []
            if address.get('village'):
                location_parts.append(address['village'])
            elif address.get('town'):
                location_parts.append(address['town'])
            elif address.get('city'):
                location_parts.append(address['city'])
            
            if address.get('state'):
                location_parts.append(address['state'])
            
            location_name = ', '.join(location_parts) if location_parts else data.get('display_name', '')
            
            return JsonResponse({
                'success': True,
                'location': location_name,
                'full_address': data.get('display_name', '')
            })
        else:
            return JsonResponse({'success': False, 'error': 'Reverse geocoding failed'}, status=500)
    
    except requests.RequestException as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)