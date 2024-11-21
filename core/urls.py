# Django and DRF
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Local
from .views import (
    SensorDataViewSet,
    HomeView,
    DevelopmentView,
    latest_data_table,
    ChartView
)


router = DefaultRouter()
router.register(r'api/sensor-data', SensorDataViewSet, basename='sensor-data')


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('latest-data-table/', latest_data_table, name='latest-data-table'),
    path('chart/', ChartView.as_view(), name='chart'),
    path('', include(router.urls)),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)