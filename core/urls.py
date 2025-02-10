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
)

router = DefaultRouter()
router.register(r'api/data-point', DataPointViewSet, basename='data-point')

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('charts/', ChartsView.as_view(), name='charts'),
    path('overview/', OverviewView.as_view(), name='overview'),
    path('sensors/', SensorsView.as_view(), name='sensors'),
    path('vpd/', VPDView.as_view(), name='vpd'),
    path('gauges/', GaugesView.as_view(), name='gauges'),
    path('', include(router.urls)),
]
