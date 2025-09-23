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
    def _make_request_with_retry(self, url: str, headers: Dict, json: Dict = None, method: str = 'get', max_retries: int = 1) -> Dict:
        """Make a request with minimal retry for faster response on Render"""
        for attempt in range(max_retries):
            try:
                if method.lower() == 'post':
                    response = requests.post(url, headers=headers, json=json, timeout=8)  # Reduced from 15s
                else:
                    response = requests.get(url, headers=headers, timeout=8)
                
                # For 400 errors, return empty dict immediately as these won't succeed with retry
                if response.status_code == 400:
                    error_msg = f"Bad request for {url}"
                    if hasattr(response, 'text'):
                        error_msg += f"\nResponse: {response.text}"
                    print(error_msg)
                    return {}
                
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                if attempt == max_retries - 1:  # Last attempt failed
                    error_msg = f"Request failed after {max_retries} attempts for {url}: {str(e)}"
                    print(error_msg)
                    return {}
                # Only retry on network errors or 5xx errors
                if not hasattr(e, 'response') or (500 <= e.response.status_code < 600):
                    continue  # Removed sleep delay for speed
                return {}
        return {}

    def format_place_data(self, place: Dict, details: Dict = None) -> Dict:
        """Format place data with all available details"""
        details = details or {}
        # Extract address
        full_address = place.get('formattedAddress', 'Address not available')
        
        # Get phone number and validate it
        phone_number = place.get('nationalPhoneNumber') or details.get('nationalPhoneNumber')
        if not phone_number:
            phone_number = place.get('internationalPhoneNumber') or details.get('internationalPhoneNumber')

        # Process opening hours - simplified for better performance
        opening_hours = place.get('currentOpeningHours') or details.get('currentOpeningHours', {})
        is_open = False
        current_opening_hours = "Hours not available"
        weekday_texts = []
        
        if opening_hours:
            weekday_texts = opening_hours.get('weekdayDescriptions', [])
            # Simplified open status check
            if opening_hours.get('openNow'):
                is_open = True
                current_opening_hours = "Open"
            elif weekday_texts:
                current_opening_hours = "Check hours"

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
            'website': details.get('websiteUri') or place.get('websiteUri') or "Not available",
            'price_level': place.get('priceLevel'),
            'business_status': place.get('businessStatus', 'OPERATIONAL'),
            'opening_hours': weekday_texts,
            'current_status': current_opening_hours,
            'is_open': is_open,
            'primary_type': place.get('types', ['PLACE'])[0].replace('_', ' ').title() if place.get('types') else 'Place',
            'short_address': place.get('shortFormattedAddress', full_address).split(',')[0],
            'has_phone': bool(phone_number)
        }

    def _sanitize_category(self, category: str) -> str:
        """Clean incoming category strings and provide a safe default."""
        if not category:
            return 'hotels'
        # Trim whitespace and stray punctuation often seen in malformed URLs
        cat = str(category).strip()
        # remove trailing/leading semicolons or equals accidentally included
        cat = cat.strip(';=').strip()
        return cat or 'hotels'

    def _get_category_from_request(self, request) -> str:
        """Robustly extract category from query params. Handles malformed keys like 'category;'."""
        # Preferred direct lookup
        category = request.query_params.get('category')
        if category:
            return self._sanitize_category(category)

        # Fallback: try to find any key that contains 'category' (covers 'category;' or similar typos)
        for key in request.query_params.keys():
            if not key:
                continue
            k = key.strip()
            if 'category' == k or k.startswith('category') or 'category' in k:
                val = request.query_params.get(key)
                if val:
                    return self._sanitize_category(val)

        # Final fallback default
        return 'hotels'

    def perform_search(self, lat: float, lng: float, category: str = 'hotels', area_size_meters: int = 5000,
                       grid_size: int = 3, overlap: float = 0.4, max_results_per_cell: int = 20) -> Dict:
        """Perform the grid search and return aggregated results dict (same shape as get response).

        This method is separated so other endpoints can call the same logic (e.g. consolidated API).
        """
        try:
            # Use the provided category only — do not expand into hardcoded synonyms.
            # This makes the API behavior deterministic: the endpoint's `category` value
            # will be passed directly as the single search keyword to Google Places.
            keywords = [category]

            # Convert meters to degrees for calculation
            earth_radius = 6378137  # meters
            step_meters = area_size_meters * (1 - overlap) * 2 / grid_size

            def offset_lat(d):
                return (d / earth_radius) * (180 / math.pi)

            def offset_lng(d, lat0):
                return (d / (earth_radius * math.cos(math.pi * lat0 / 180))) * (180 / math.pi)

            places = {}
            url = 'https://places.googleapis.com/v1/places:searchText'
            api_key = os.getenv('GOOGLE_PLACES_API_KEY')
            search_headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,'
                                  'places.rating,places.userRatingCount,places.types,places.nationalPhoneNumber,'
                                  'places.websiteUri,places.priceLevel,places.businessStatus,places.shortFormattedAddress,'
                                  'places.currentOpeningHours'
            }

            for keyword in keywords:
                for i in range(grid_size):
                    for j in range(grid_size):
                        try:
                            cache_key = f'places_search_{lat}_{lng}_{area_size_meters}_{category}_{keyword}_{i}_{j}'
                            cached_results = cache.get(cache_key)
                            if cached_results:
                                for place in cached_results:
                                    if place['place_id'] not in places:
                                        places[place['place_id']] = place
                                continue

                            offset_x = step_meters * (i - grid_size // 2)
                            offset_y = step_meters * (j - grid_size // 2)

                            lat_offset = offset_lat(offset_y)
                            lng_offset = offset_lng(offset_x, lat)

                            search_lat = lat + lat_offset
                            search_lng = lng + lng_offset
                            search_radius = int(step_meters * 0.7)

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
                                'maxResultCount': max_results_per_cell
                            }

                            data = self._make_request_with_retry(
                                url=url,
                                headers=search_headers,
                                json=payload,
                                method='post'
                            )

                            if not data or 'places' not in data:
                                cache.set(cache_key, [], timeout=3600)
                                continue

                            cell_places = []
                            for place in data['places']:
                                place_id = place.get('id')
                                if place_id and place_id not in places:
                                    formatted_place = self.format_place_data(place, None)
                                    places[place_id] = formatted_place
                                    cell_places.append(formatted_place)

                            cache.set(cache_key, cell_places, timeout=3600)
                        except Exception as e:
                            print(f"Error in grid cell {i},{j} for keyword {keyword}: {str(e)}")
                            continue

            response_data = {
                'results': list(places.values()),
                'metadata': {
                    'total_results': len(places),
                    'search_parameters': {
                        'latitude': lat,
                        'longitude': lng,
                        'area_size_km': area_size_meters / 1000,
                        'cell_radius_m': int(step_meters / 2),
                        'keywords': keywords,
                        'grid_size': grid_size,
                        'overlap': overlap
                    },
                    'timestamp': datetime.now().isoformat()
                }
            }
            return response_data
        except Exception as e:
            print(f"perform_search error: {str(e)}")
            raise

    def get(self, request):
        try:
            lat = request.query_params.get('latitude')
            lng = request.query_params.get('longitude')
            category = self._get_category_from_request(request)

            if not (lat and lng):
                return Response({'error': 'latitude and longitude are required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                lat = float(lat)
                lng = float(lng)
            except ValueError:
                return Response({'error': 'Invalid latitude or longitude.'}, status=status.HTTP_400_BAD_REQUEST)

            area_size_param = request.query_params.get('area_size')
            area_size_meters = int(area_size_param) if area_size_param else 5000
            grid_size = int(request.query_params.get('grid_size', 3))
            overlap = float(request.query_params.get('overlap', 0.4))

            response_data = self.perform_search(lat=lat, lng=lng, category=category,
                                                area_size_meters=area_size_meters,
                                                grid_size=grid_size, overlap=overlap)
            return Response(response_data)
        except Exception as e:
            print(f"Main search error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': f'Search failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConsolidatedPlacesAPI(GooglePlacesHotelSearchView):
    """A single API endpoint intended for frontend integration.

    Accepts either `address` (preferred) or `latitude`+`longitude`, plus `category` and optional grid params.
    Returns JSON with `results` and `metadata` ready for frontend rendering.
    """
    def get(self, request):
        try:
            address = request.query_params.get('address')
            lat = request.query_params.get('latitude')
            lng = request.query_params.get('longitude')
            category = self._get_category_from_request(request)

            area_size_param = request.query_params.get('area_size')
            area_size_meters = int(area_size_param) if area_size_param else 5000
            grid_size = int(request.query_params.get('grid_size', 3))
            overlap = float(request.query_params.get('overlap', 0.4))

            # If address is provided, do a quick geocode (use the same Places searchText)
            if address and not (lat and lng):
                api_key = os.getenv('GOOGLE_PLACES_API_KEY')
                if not api_key:
                    return Response({'error': 'Google API key is not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                geocode_url = 'https://places.googleapis.com/v1/places:searchText'
                headers = {
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Key': api_key,
                    'X-Goog-FieldMask': 'places.location,places.formattedAddress'
                }
                payload = {'textQuery': address}
                data = self._make_request_with_retry(url=geocode_url, headers=headers, json=payload, method='post')
                if not data or 'places' not in data or not data['places']:
                    return Response({'error': 'Address geocoding failed or no location found'}, status=status.HTTP_404_NOT_FOUND)
                place = data['places'][0]
                location = place.get('location', {})
                lat = location.get('latitude')
                lng = location.get('longitude')
                if lat is None or lng is None:
                    return Response({'error': 'Failed to obtain coordinates from address'}, status=status.HTTP_404_NOT_FOUND)

            if not (lat and lng):
                return Response({'error': 'Provide either address or latitude and longitude.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                lat = float(lat)
                lng = float(lng)
            except ValueError:
                return Response({'error': 'Invalid latitude or longitude values.'}, status=status.HTTP_400_BAD_REQUEST)

            response_data = self.perform_search(lat=lat, lng=lng, category=category,
                                                area_size_meters=area_size_meters, grid_size=grid_size, overlap=overlap)
            return Response(response_data)
        except Exception as e:
            print(f"Consolidated API error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': f'Consolidated search failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                # Use standard 5km area size for consistency
                area_size = 5000
            else:
                # Default search area (5km radius for consistency)
                area_size = 5000
                bounds = {
                    'northeast': {
                        'lat': location["latitude"] + 0.045,  # Approximately 5km
                        'lng': location["longitude"] + 0.045
                    },
                    'southwest': {
                        'lat': location["latitude"] - 0.045,
                        'lng': location["longitude"] - 0.045
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
                        'grid_size': 3,  # Match backend default (3x3 grid)
                        'overlap': 0.4,  # Match backend default (40% overlap)
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
