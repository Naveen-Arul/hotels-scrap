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
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')

        if not (lat and lng):
            return Response(
                {'error': 'latitude and longitude are required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not api_key:
            return Response(
                {'error': 'Google API key is not configured'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            lat = float(lat)
            lng = float(lng)
            # Get area size from request or use default
            area_size = request.query_params.get('area_size')
            area_size = int(area_size) if area_size else 2000  # Very small radius for dense results
        except ValueError:
            return Response(
                {'error': 'Invalid latitude or longitude.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get category from request parameter
            category = request.query_params.get('category', 'hotels')  # Default to hotels if not provided
            print(f"Searching for category: {category}")  # Debug log
            
            # Get grid parameters from request or use defaults
            grid_size = int(request.query_params.get('grid_size', 8))   # Moderate grid size
            overlap = float(request.query_params.get('overlap', 0.8))   # Very high overlap for dense coverage
            
            earth_radius = 6378137  # meters
            step = area_size * (1 - overlap) * 2 / grid_size

            def offset_lat(d):
                return (d / earth_radius) * (180 / math.pi)

            def offset_lng(d, lat0):
                return (d / (earth_radius * math.cos(math.pi * lat0 / 180))) * (180 / math.pi)

            places = {}
            url = 'https://places.googleapis.com/v1/places:searchText'
            search_headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.types,places.nationalPhoneNumber,places.websiteUri,places.priceLevel,places.businessStatus'
            }
            
            # Calculate grid spacing
            step_lat = offset_lat(area_size) * (1 - overlap)
            step_lng = offset_lng(area_size, lat) * (1 - overlap)
            
            print(f"Search configuration: {grid_size}x{grid_size} grid, {area_size}m radius, {overlap} overlap")
            print(f"Grid step: lat={step_lat:.6f}°, lng={step_lng:.6f}°")
            
            # Calculate grid bounds
            half_grid = (grid_size - 1) / 2
            start_lat = lat - half_grid * step_lat
            start_lng = lng - half_grid * step_lng
            
            print(f"Grid bounds: lat {start_lat:.6f} to {lat + half_grid * step_lat:.6f}, lng {start_lng:.6f} to {lng + half_grid * step_lng:.6f}")
            
            # Search each grid cell
            for i in range(grid_size):
                for j in range(grid_size):
                    grid_lat = start_lat + i * step_lat
                    grid_lng = start_lng + j * step_lng
                    
                    # Search payload for this grid cell
                    payload = {
                        'textQuery': category,  # Use dynamic category from user input
                        'locationBias': {
                            'circle': {
                                'center': {
                                    'latitude': grid_lat,
                                    'longitude': grid_lng
                                },
                                'radius': area_size
                            }
                        },
                        'maxResultCount': 20
                    }

                    # Make the API request for this grid cell
                    print(f"Searching grid cell {i+1},{j+1}/{grid_size}x{grid_size} at lat:{grid_lat:.6f}, lng:{grid_lng:.6f} for {category}")
                    data = self._make_request_with_retry(
                        url=url,
                        headers=search_headers,
                        json=payload,
                        method='post'
                    )
                    
                    if data and 'places' in data:
                        new_places_count = 0
                        for place in data['places']:
                            place_id = place.get('id')
                            if place_id and place_id not in places:  # Avoid duplicates
                                formatted_place = self.format_place_data(place, place)
                                places[place_id] = formatted_place
                                new_places_count += 1
                        print(f"Grid cell {i+1},{j+1}: Found {len(data.get('places', []))} places, {new_places_count} new unique places. Total so far: {len(places)}")
                    else:
                        print(f"Grid cell {i+1},{j+1}: No data returned or API error")

            # Prepare final response with metadata
            response_data = {
                'results': list(places.values()),
                'metadata': {
                    'total_results': len(places),
                    'grid_searches_performed': grid_size * grid_size,
                    'search_parameters': {
                        'category': category,
                        'latitude': lat,
                        'longitude': lng,
                        'area_size': area_size,
                        'grid_size': grid_size,
                        'overlap': overlap,
                        'area_size_km': area_size / 1000
                    },
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            print(f"Grid search completed: {len(places)} {category} found from {grid_size}x{grid_size} grid")
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': f'Search failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GoogleGeocodingView(APIView):
    def get(self, request):
        address = request.query_params.get('address')
        region_code = request.query_params.get('region', 'in')  # Default to 'in' but allow override
        
        if not address:
            return Response(
                {'error': 'Address parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not api_key:
            return Response(
                {'error': 'Google API key is not configured'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.formattedAddress,places.location,places.types,places.viewport"
        }
        payload = {
            "textQuery": address,
            "regionCode": region_code  # Use configured region code
        }

        try:
            print(f"Calling Places API for address: {address}")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            data = response.json()
            
            print(f"Places API response status: {response.status_code}")
            print(f"Places API response: {data}")
            
            if "places" not in data or not data["places"]:
                return Response(
                    {"error": "No location found for this address"},
                    status=status.HTTP_404_NOT_FOUND
                )

            place = data["places"][0]
            location = place.get("location", {})
            
            # Use viewport for search area if available, otherwise use default
            viewport = place.get("viewport", {})
            if viewport and viewport.get("high") and viewport.get("low"):
                bounds = {
                    'northeast': {
                        'lat': viewport["high"]["latitude"],
                        'lng': viewport["high"]["longitude"]
                    },
                    'southwest': {
                        'lat': viewport["low"]["latitude"],
                        'lng': viewport["low"]["longitude"]
                    }
                }
                # Calculate approximate size in meters based on viewport
                lat_diff = abs(viewport["high"]["latitude"] - viewport["low"]["latitude"])
                lng_diff = abs(viewport["high"]["longitude"] - viewport["low"]["longitude"])
                area_size = int(
                    min(
                        max(
                            math.sqrt(
                                (lat_diff * 111000) ** 2 + 
                                (lng_diff * 111000 * math.cos(math.radians(location["latitude"]))) ** 2
                            ),
                            1000  # Minimum 1km
                        ),
                        5000  # Maximum 5km
                    )
                )
            else:
                # Default search area (2km radius)
                area_size = 2000
                bounds = {
                    'northeast': {
                        'lat': location["latitude"] + 0.018,  # Approximately 2km
                        'lng': location["longitude"] + 0.018
                    },
                    'southwest': {
                        'lat': location["latitude"] - 0.018,
                        'lng': location["longitude"] - 0.018
                    }
                }

            response_data = {
                'results': [{
                    'formatted_address': place.get("formattedAddress", address),
                    'geometry': {
                        'location': {
                            'lat': location["latitude"],
                            'lng': location["longitude"]
                        },
                        'bounds': bounds
                    },
                    'area_info': {
                        'type': place.get("types", ["UNKNOWN"])[0],
                        'name': place.get("formattedAddress", address),
                        'grid_size': 7,  # Use fixed grid size
                        'overlap': 0.5,  # Use fixed overlap
                        'area_size': area_size
                    }
                }]
            }
            return Response(response_data)

        except Exception as e:
            print(f"Places API error: {str(e)}")  # Debug log
            return Response(
                {"error": f"Failed to geocode address: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
