from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    # Public endpoints
    path('lookup/<str:vin>/', views.lookup_vin, name='lookup_vin'),
    path('plate/<str:plate>/', views.plate_to_vin, name='plate_to_vin'),

    # Authenticated endpoints
    path('full/<str:vin>/', views.full_vehicle_report, name='full_report'),
    path('search/', views.search_vehicles, name='search'),

    # Admin/staff endpoints
    path('enrich/<str:vin>/', views.manual_enrich, name='manual_enrich'),
]