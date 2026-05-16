# reports/geocoding_utils.py
import requests
import logging
import re
from django.conf import settings

logger = logging.getLogger(__name__)

# Known Nigerian coordinates for common locations (fallback)
NIGERIAN_LOCATIONS = {
    # Major Cities
    'abuja': (9.0765, 7.3986),
    'lagos': (6.5244, 3.3792),
    'kano': (12.0022, 8.5919),
    'ibadan': (7.3775, 3.9470),
    'benin': (6.3176, 5.6145),
    'port harcourt': (4.8156, 7.0498),
    'enugu': (6.4500, 7.5000),
    'aba': (5.1067, 7.3667),
    'onitsha': (6.1498, 6.7859),
    'warri': (5.5173, 5.7506),
    'jos': (9.8965, 8.8583),
    'kaduna': (10.5105, 7.4165),
    'maiduguri': (11.8333, 13.1500),
    'sokoto': (13.0059, 5.2476),
    'abakaliki': (6.3333, 8.1000),
    'akure': (7.2526, 5.1931),
    'bauchi': (10.3104, 9.8459),
    'calabar': (4.9583, 8.3250),
    'damaturu': (11.7476, 11.9661),
    'dutse': (11.7615, 9.3387),
    'ekiti': (7.7337, 5.2980),
    'gombe': (10.2897, 11.1673),
    'gusu': (12.1700, 6.6667),
    'ibadan': (7.3775, 3.9470),
    'ijebu ode': (6.8167, 3.9167),
    'ikeja': (6.6018, 3.3515),
    'ilorin': (8.5000, 4.5500),
    'jalingo': (8.8833, 11.3667),
    'katsina': (12.9907, 7.6018),
    'kebbi': (12.4500, 4.2000),
    'lafia': (8.4900, 8.5200),
    'lokoja': (7.8023, 6.7413),
    'makurdi': (7.7325, 8.5391),
    'minna': (9.5833, 6.5500),
    'nguru': (12.8833, 10.4500),
    'nnewi': (6.0167, 6.9167),
    'numan': (9.4667, 12.0333),
    'oke-ira': (6.6000, 3.3500),
    'oke ira': (6.6000, 3.3500),
    'owerri': (5.4833, 7.0333),
    'oyo': (7.8500, 3.9333),
    'potiskum': (11.7167, 11.0667),
    'sapele': (5.8947, 5.6767),
    'ughelli': (5.5000, 5.9833),
    'uleja': (7.2500, 6.6667),
    'umuahia': (5.5333, 7.4833),
    'uyo': (5.0333, 7.9167),
    'yola': (9.2333, 12.4667),
    'zaria': (11.0833, 7.7000),
    
    # Markets and specific places
    'gwagwalada market': (8.9333, 7.0833),
    'oke-ira ogba': (6.6000, 3.3500),
    'oke ira ogba lagos': (6.6000, 3.3500),
    'umudim village': (5.5333, 7.4833),
    'umudim': (5.5333, 7.4833),
    
    # States (approximate centers)
    'abia': (5.4167, 7.5000),
    'adamawa': (9.3333, 12.5000),
    'akwa ibom': (4.9167, 8.0000),
    'anambra': (6.2500, 6.9167),
    'bauchi': (10.5000, 10.0000),
    'bayelsa': (4.7500, 6.0833),
    'benue': (7.3333, 8.7500),
    'borno': (11.5000, 13.0000),
    'cross river': (5.7500, 8.5000),
    'delta': (5.7500, 6.2500),
    'ebonyi': (6.2500, 8.0833),
    'edo': (6.5000, 6.0000),
    'ekiti': (7.6667, 5.2500),
    'enugu': (6.5000, 7.5000),
    'gombe': (10.5000, 11.5000),
    'imo': (5.5000, 7.0000),
    'jigawa': (12.0000, 9.7500),
    'kaduna': (10.5000, 7.5000),
    'kano': (11.5000, 8.5000),
    'katsina': (12.5000, 7.5000),
    'kebbi': (11.0000, 4.0000),
    'kogi': (7.8000, 6.7500),
    'kwara': (8.5000, 4.5000),
    'lagos': (6.5244, 3.3792),
    'nasarawa': (8.5000, 8.0000),
    'niger': (9.5833, 6.5500),
    'ogun': (7.0000, 3.5000),
    'ondo': (7.0000, 5.0000),
    'osun': (7.5000, 4.5000),
    'oyo': (7.8500, 3.9333),
    'plateau': (9.5000, 9.5000),
    'rivers': (4.7500, 6.8333),
    'sokoto': (13.0000, 5.2500),
    'taraba': (8.0000, 10.5000),
    'yobe': (12.0000, 11.5000),
    'zamfara': (12.0000, 6.0000),
}


def clean_location_text(text):
    """Clean and normalize location text for better matching"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove common punctuation
    text = re.sub(r'[^\w\s,]', '', text)
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    return text


def find_in_fallback_database(location_text):
    """Check if location exists in our local database"""
    cleaned = clean_location_text(location_text)
    
    # Direct match
    if cleaned in NIGERIAN_LOCATIONS:
        return NIGERIAN_LOCATIONS[cleaned]
    
    # Partial match - check if any key is contained in the location text
    for key, coords in NIGERIAN_LOCATIONS.items():
        if key in cleaned or cleaned in key:
            return coords
    
    return None


def geocode_with_nominatim(location_text):
    """Geocode using OpenStreetMap Nominatim API"""
    try:
        # Clean and prepare the query
        query = f"{location_text}, Nigeria"
        
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'q': query,
                'format': 'json',
                'limit': 3,
                'countrycodes': 'ng,gh,ke,za,ci,sn,cm',
                'accept-language': 'en'
            },
            headers={'User-Agent': 'GridWatch/2.0 (https://gridwatch.com)'},
            timeout=8
        )
        
        if response.status_code == 200:
            results = response.json()
            if results:
                # Return the first result
                lat = float(results[0].get('lat', 0))
                lon = float(results[0].get('lon', 0))
                display_name = results[0].get('display_name', '')
                logger.info(f"Nominatim found: {display_name} -> ({lat}, {lon})")
                return lat, lon
        return None, None
        
    except requests.exceptions.Timeout:
        logger.warning(f"Nominatim timeout for '{location_text}'")
        return None, None
    except Exception as e:
        logger.warning(f"Nominatim error for '{location_text}': {e}")
        return None, None


def geocode_with_google(location_text):
    """Geocode using Google Maps API (requires API key)"""
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    
    if not api_key:
        return None, None
    
    try:
        response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={
                'address': f"{location_text}, Nigeria",
                'key': api_key,
                'region': 'ng'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and len(data['results']) > 0:
                location = data['results'][0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                logger.info(f"Google Maps found: {data['results'][0]['formatted_address']} -> ({lat}, {lng})")
                return lat, lng
        return None, None
        
    except Exception as e:
        logger.warning(f"Google Maps error for '{location_text}': {e}")
        return None, None


def geocode_location(location_text, use_fallback=True):
    """
    Convert a location text to coordinates using multiple strategies.
    Returns (latitude, longitude) tuple or (None, None) if not found.
    """
    if not location_text or not location_text.strip():
        return None, None
    
    logger.info(f"Geocoding location: '{location_text}'")
    
    # Strategy 1: Check local fallback database first (fastest)
    coords = find_in_fallback_database(location_text)
    if coords:
        logger.info(f"Found in local database: ({coords[0]}, {coords[1]})")
        return coords
    
    # Strategy 2: Try Nominatim (OpenStreetMap)
    lat, lng = geocode_with_nominatim(location_text)
    if lat and lng:
        return lat, lng
    
    # Strategy 3: Try Google Maps (if API key configured)
    lat, lng = geocode_with_google(location_text)
    if lat and lng:
        return lat, lng
    
    # Strategy 4: Extract state or city from location and try again
    # Try to extract the last part of location (likely state or major city)
    parts = location_text.split(',')
    if len(parts) > 1:
        last_part = parts[-1].strip()
        coords = find_in_fallback_database(last_part)
        if coords:
            logger.info(f"Using fallback based on state/city '{last_part}': ({coords[0]}, {coords[1]})")
            return coords
    
    # Strategy 5: Use Nigeria center as absolute fallback
    logger.warning(f"Could not geocode '{location_text}', using Nigeria center")
    return 9.0820, 8.6753  # Center of Nigeria


def batch_geocode_existing_reports():
    """
    Update existing reports that don't have coordinates.
    Run this as a management command or via Django shell.
    """
    from .models import OutageReport
    
    reports = OutageReport.objects.filter(
        latitude__isnull=True, 
        longitude__isnull=True
    )
    
    updated_count = 0
    failed_count = 0
    
    for report in reports:
        lat, lon = geocode_location(report.location_text)
        if lat and lon:
            report.latitude = lat
            report.longitude = lon
            report.save()
            updated_count += 1
            logger.info(f"✅ Updated {report.report_id}: '{report.location_text}' -> ({lat}, {lon})")
        else:
            failed_count += 1
            logger.warning(f"❌ Failed to geocode {report.report_id}: '{report.location_text}'")
    
    logger.info(f"Geocoding complete. Updated: {updated_count}, Failed: {failed_count}")
    return updated_count


def geocode_user_villages():
    """
    Geocode all users' villages and save coordinates to their profile.
    Run this as a management command.
    """
    from django.contrib.auth import get_user_model
    from .models import Profile
    
    User = get_user_model()
    updated_count = 0
    
    for user in User.objects.filter(village__isnull=False, village__gt=''):
        lat, lon = geocode_location(user.village)
        if lat and lon:
            # You can add latitude/longitude fields to the user model or profile
            # For now, we just log it
            print(f"User {user.email}: {user.village} -> ({lat}, {lon})")
            updated_count += 1
    
    return updated_count