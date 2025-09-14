from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
import views

def home(request):
    return HttpResponse("""
    <h1>🏨 Hotels Scrap API is Live! 🎉</h1>
    <p>Your Django app is successfully deployed on Render!</p>
    <h3>Available Endpoints:</h3>
    <ul>
        <li><a href="/search/">/search/</a> - Hotel search API</li>
        <li><a href="/geocode/">/geocode/</a> - Geocoding API</li>
        <li><a href="/hotel_map.html">/hotel_map.html</a> - Hotel Map Frontend</li>
    </ul>
    <p><strong>Deployment Status:</strong> ✅ SUCCESS</p>
    """)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),  # Homepage
    path('search/', views.GooglePlacesHotelSearchView.as_view(), name='places-search'),
    path('geocode/', views.GoogleGeocodingView.as_view(), name='geocode'),
]
