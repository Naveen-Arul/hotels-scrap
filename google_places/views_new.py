import os
import requests
import math
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache

class GooglePlacesHotelSearchView(APIView):
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
