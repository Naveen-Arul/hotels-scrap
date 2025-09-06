from django.contrib import admin
from django.urls import path
from views import GooglePlacesHotelSearchView, GoogleGeocodingView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('search/', GooglePlacesHotelSearchView.as_view(), name='places-search'),
    path('geocode/', GoogleGeocodingView.as_view(), name='geocode'),
]
