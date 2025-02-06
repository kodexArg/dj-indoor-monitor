# Django y DRF
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Local
from .api import SensorDataViewSet, DataPointViewSet
from .views import (
    HomeView,
    DevelopmentView,
    OldDevicesChartView,
    ChartsView,
    OverviewView,
    SensorsView,
    GaugesView,
    GenerateGaugeView,  # Eliminado GaugeComponentView, solo dejamos GenerateGaugeView
    VPDView,
)

router = DefaultRouter()
router.register(r'api/sensor-data', SensorDataViewSet, basename='sensor-data')
router.register(r'api/data-point', DataPointViewSet, basename='data-point')

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('old-devices/', OldDevicesChartView.as_view(), name='old-devices'),
    path('charts/', ChartsView.as_view(), name='charts'),
    path('overview/', OverviewView.as_view(), name='overview'),
    path('gauges/', GaugesView.as_view(), name='gauges'),
    path('sensors/', SensorsView.as_view(), name='sensors'),
    path('vpd/', VPDView.as_view(), name='vpd'),
    path('timeframed/', SensorDataViewSet.as_view({'get': 'timeframed'}), name='timeframed'), # shortcut for /api/sensor-data/timeframed/
    path('generate-gauge/', GenerateGaugeView.as_view(), name='generate-gauge'),
    path('gauge-component/', GenerateGaugeView.as_view(), name='gauge-component'),
    path('', include(router.urls)),
]
