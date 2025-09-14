from django.contrib import admin
from django.urls import path
import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('search/', views.GooglePlacesHotelSearchView.as_view(), name='places-search'),
    path('geocode/', views.GoogleGeocodingView.as_view(), name='geocode'),
]
