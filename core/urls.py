# Django y DRF
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Local
from .api import SensorDataViewSet
from .views import (
    HomeView,
    DevelopmentView,
    OldDevicesChartView,
    ChartsView,
    OverviewView,
    SensorsView,
    GaugesView,
    VPDView,
)

router = DefaultRouter()
router.register(r'api/sensor-data', SensorDataViewSet, basename='sensor-data')

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('old-devices/', OldDevicesChartView.as_view(), name='old-devices'),
    path('charts/', ChartsView.as_view(), name='charts'),
    path('overview/', OverviewView.as_view(), name='overview'),
    path('gauges/', GaugesView.as_view(), name='gauges'),
    path('sensors/', SensorsView.as_view(), name='sensors'),
    path('vpd/', VPDView.as_view(), name='vpd'),
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)