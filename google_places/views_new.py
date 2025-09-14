import os
import requests
import math
import time
from datetime import datetime
from typing import Dict, List
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache

class GooglePlacesHotelSearchView(APIView):
    def _make_request_with_retry(self, url: str, headers: Dict, json: Dict = None, method: str = 'get', max_retries: int = 3) -> Dict:
        """Make a request with retry logic"""
        import ssl
        import urllib3
        
        # Disable SSL warnings for production deployment
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        for attempt in range(max_retries):
            try:
                # Add SSL verification bypass for Render deployment
                session = requests.Session()
                session.verify = False  # Bypass SSL verification
                
                if method.lower() == 'post':
                    response = session.post(url, headers=headers, json=json, timeout=30)
                else:
                    response = session.get(url, headers=headers, timeout=30)
                
                # For 400 errors, return empty dict immediately as these won't succeed with retry
                if response.status_code == 400:
                    error_msg = f"Bad request for {url}"
                    if hasattr(response, 'text'):
                        error_msg += f"\nResponse: {response.text}"
                    print(error_msg)
                    return {}
                
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt failed
                    print(f"All {max_retries} attempts failed for {url}: {str(e)}")
                    # Return a mock response to prevent total failure
                    return {"results": [], "error": "API temporarily unavailable"}
                time.sleep(2 * (attempt + 1))  # Progressive delay
                continue
        return {"results": [], "error": "Request failed"}

    def format_place_data(self, place: Dict, details: Dict = None) -> Dict:
        """Format place data with all available details"""
        details = details or {}
        # Extract address
        full_address = place.get('formattedAddress', 'Address not available')
        
        # Get phone number and validate it
        phone_number = place.get('nationalPhoneNumber') or details.get('nationalPhoneNumber')
        if not phone_number:
            phone_number = place.get('internationalPhoneNumber') or details.get('internationalPhoneNumber')

        # Process opening hours
        opening_hours = place.get('currentOpeningHours') or details.get('currentOpeningHours', {})
        is_open = False
        current_opening_hours = "Closed"
        
        if opening_hours:
            # Check if the place is currently open
            weekday_texts = opening_hours.get('weekdayDescriptions', [])
            periods = opening_hours.get('periods', [])
            if periods:
                now = datetime.now()
                current_weekday = now.weekday()
                current_time = now.strftime('%H:%M')
                
                for period in periods:
                    if period.get('open', {}).get('day') == current_weekday:
                        open_time = period.get('open', {}).get('time', '')
                        close_time = period.get('close', {}).get('time', '')
                        if open_time and close_time and open_time <= current_time <= close_time:
                            is_open = True
                            current_opening_hours = "Open"
                            break

        return {
            'place_id': place['id'],
            'name': place.get('displayName', {}).get('text', 'Unnamed Place'),
            'formatted_address': full_address,
            'location': {
                'latitude': place.get('location', {}).get('latitude'),
                'longitude': place.get('location', {}).get('longitude')
            },
            'rating': place.get('rating'),
            'user_ratings_total': place.get('userRatingCount', 0),
            'types': place.get('types', []),
            'phone_number': phone_number or "Not available",
            'website': details.get('websiteUri') or place.get('websiteUri'),
            'price_level': place.get('priceLevel'),
            'business_status': place.get('businessStatus', 'OPERATIONAL'),
            'opening_hours': weekday_texts if 'weekday_texts' in locals() and weekday_texts else [],
            'current_status': current_opening_hours,
            'is_open': is_open,
            'primary_type': place.get('types', ['PLACE'])[0].replace('_', ' ').title(),
            'short_address': place.get('shortFormattedAddress', full_address).split(',')[0],
            'has_phone': bool(phone_number)
        }
    def get(self, request):
        # Get query parameters
        lat = request.query_params.get('latitude')
        lng = request.query_params.get('longitude')
        radius = request.query_params.get('radius')
        search_type = request.query_params.get('type', 'hotels')
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')

        if not (lat and lng and radius):
            return Response(
                {'error': 'latitude, longitude, and radius are required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lat = float(lat)
            lng = float(lng)
            radius_m = int(float(radius) * 1000)  # convert km to meters
        except ValueError:
            return Response(
                {'error': 'Invalid latitude, longitude, or radius.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Define search parameters
        keywords = ['hotels', 'restaurants', 'mess', 'canteens']
        grid_size = 3
        overlap = 0.5  # 50% overlap
        earth_radius = 6378137  # meters
        step = radius_m * (1 - overlap) * 2 / grid_size

        def offset_lat(d):
            return (d / earth_radius) * (180 / math.pi)

        def offset_lng(d, lat0):
            return (d / (earth_radius * math.cos(math.pi * lat0 / 180))) * (180 / math.pi)

        places = {}
        url = 'https://places.googleapis.com/v1/places:searchText'
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'places.*'
        }

        for keyword in keywords:
            for i in range(grid_size):
                for j in range(grid_size):
                    # Calculate search coordinates for this grid cell
                    offset_x = step * (i - grid_size // 2)
                    offset_y = step * (j - grid_size // 2)
                    
                    lat_offset = offset_lat(offset_y)
                    lng_offset = offset_lng(offset_x, lat)
                    
                    search_lat = lat + lat_offset
                    search_lng = lng + lng_offset
                    search_radius = int(step / 2)  # Use half the step size as search radius

                    # Prepare the request payload
                    payload = {
                        'textQuery': keyword,
                        'locationBias': {
                            'circle': {
                                'center': {
                                    'latitude': search_lat,
                                    'longitude': search_lng
                                },
                                'radius': search_radius
                            }
                        },
                        'maxResultCount': 20
                    }

                    # Make the API request
                    try:
                        response = requests.post(url, headers=headers, json=payload)
                        if response.status_code == 200:
                            data = response.json()
                            if 'places' in data:
                                for place in data['places']:
                                    place_id = place.get('id')
                                    if place_id not in places:
                                        # Process and format place data
                                        formatted_place = {
                                            'place_id': place_id,
                                            'name': place.get('displayName', {}).get('text', 'Unnamed Place'),
                                            'formatted_address': place.get('formattedAddress', 'Address not available'),
                                            'location': {
                                                'latitude': place.get('location', {}).get('latitude'),
                                                'longitude': place.get('location', {}).get('longitude')
                                            },
                                            'rating': place.get('rating'),
                                            'user_ratings_total': place.get('userRatingCount'),
                                            'types': place.get('types', []),
                                            'vicinity': place.get('formattedAddress'),
                                            'international_phone_number': place.get('internationalPhoneNumber'),
                                            'formatted_phone_number': place.get('nationalPhoneNumber'),
                                            'website': place.get('websiteUri'),
                                            'business_status': place.get('businessStatus'),
                                            'opening_hours': {
                                                'open_now': place.get('currentOpeningHours', {}).get('openNow'),
                                                'periods': place.get('currentOpeningHours', {}).get('periods', [])
                                            },
                                            'price_level': place.get('priceLevel')
                                        }
                                        places[place_id] = formatted_place

                    except requests.exceptions.RequestException as e:
                        print(f"Error in grid cell ({i},{j}): {e}")
                        continue  # Skip this cell and continue with the next one

        # Prepare final response with metadata
        response_data = {
            'results': list(places.values()),
            'metadata': {
                'total_results': len(places),
                'search_parameters': {
                    'latitude': lat,
                    'longitude': lng,
                    'radius_km': float(radius),
                    'type': search_type
                },
                'timestamp': datetime.now().isoformat()
            }
        }

        return Response(response_data)
