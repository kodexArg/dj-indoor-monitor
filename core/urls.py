from django.contrib import admin
from django.urls import path
from .views import SensorDataAPIView, HomeView, DevelopmentView, latest_data_table

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('api/sensor-data/', SensorDataAPIView.as_view(), name='sensor-data'),
    path('api/sensor-data/<str:raspberry_pi_id>/', SensorDataAPIView.as_view(), name='sensor-data-by-rpi'),
    path('latest-data-table/', latest_data_table, name='latest-data-table'),
]