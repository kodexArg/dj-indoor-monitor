from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    SensorDataListView,
    SensorDataCreateAPIView,
    HomeView,
    DevelopmentView,
    latest_data_table,
    latest_data_chart
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('api/sensor-data/', SensorDataListView.as_view(), name='sensor-data-list'),
    path('api/sensor-data/create/', SensorDataCreateAPIView.as_view(), name='sensor-data-create'),
    path('latest-data-table/', latest_data_table, name='latest-data-table'),
    path('latest-data-chart/', latest_data_chart, name='latest-data-chart'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)