from django.urls import path
from django.http import HttpResponse
import views
import health
import os

def hotel_map_home(request):
    """Serve the hotel map as the only page"""
    try:
        # Read the hotel_map.html file
        file_path = os.path.join(os.path.dirname(__file__), 'hotel_map.html')
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HttpResponse(html_content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse("Hotel map not found", status=404)

urlpatterns = [
    path('', hotel_map_home, name='home'),  # ONLY hotel map - nothing else
    path('search/', views.GooglePlacesHotelSearchView.as_view(), name='places-search'),
    path('geocode/', views.GoogleGeocodingView.as_view(), name='geocode'),
    path('health/', health.HealthCheckView.as_view(), name='health-check'),
]
