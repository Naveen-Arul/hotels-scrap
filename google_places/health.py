import os
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class HealthCheckView(APIView):
    def get(self, request):
        """Simple health check to test environment variables and basic functionality"""
        try:
            api_key = os.getenv('GOOGLE_PLACES_API_KEY')
            
            # Test basic info
            health_data = {
                'status': 'healthy',
                'api_key_configured': bool(api_key),
                'api_key_length': len(api_key) if api_key else 0,
                'environment_variables': {
                    'GOOGLE_PLACES_API_KEY': 'SET' if api_key else 'NOT SET',
                },
                'python_version': os.sys.version,
                'working_directory': os.getcwd(),
            }
            
            # Test a simple Google API call
            if api_key:
                try:
                    test_url = 'https://places.googleapis.com/v1/places:searchText'
                    test_headers = {
                        'Content-Type': 'application/json',
                        'X-Goog-Api-Key': api_key,
                        'X-Goog-FieldMask': 'places.id,places.displayName'
                    }
                    test_payload = {
                        'textQuery': 'hotel',
                        'locationBias': {
                            'circle': {
                                'center': {'latitude': 11.2746098, 'longitude': 77.5827007},
                                'radius': 5000
                            }
                        },
                        'maxResultCount': 1
                    }
                    
                    response = requests.post(test_url, headers=test_headers, json=test_payload, timeout=10)
                    health_data['api_test'] = {
                        'status_code': response.status_code,
                        'success': response.status_code == 200,
                        'response_preview': str(response.text)[:200] if response.text else 'No response text'
                    }
                except Exception as e:
                    health_data['api_test'] = {
                        'error': str(e),
                        'success': False
                    }
            
            return Response(health_data)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e),
                'api_key_configured': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)