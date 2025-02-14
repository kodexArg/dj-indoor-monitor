# Django y DRF
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Local
from .api import DataPointViewSet
from .views import (
    HomeView,
    DevelopmentView,
    ChartsView,
    OverviewView,
    SensorsView,
    VPDView,
    GaugesView,
    GenerateGaugeView,
    GenerateSensorView
)

router = DefaultRouter()
router.register(r'api/data-point', DataPointViewSet, basename='data-point')

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('charts/', ChartsView.as_view(), name='charts'),
    path('charts/overview/', OverviewView.as_view(), name='overview'),
    path('charts/sensors/', SensorsView.as_view(), name='sensors'),
    path('charts/vpd/', VPDView.as_view(), name='vpd'),
    path('charts/gauges/', GaugesView.as_view(), name='gauges'),
    path('generate_gauge/', GenerateGaugeView.as_view(), name='generate-gauge'),
    path('generate_sensor/', GenerateSensorView.as_view(), name='generate-sensor'),
    path('', include(router.urls)),
]
