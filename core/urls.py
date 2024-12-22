# Django y DRF
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from django.views.generic import TemplateView

# Local
from .views import (
    SensorDataViewSet,
    HomeView,
    ChartsView,
    ChartView,
    DualChartView,
    GaugesView,
    TableCoefView,
    DevelopmentView,
    OldDevicesChartView,
)

router = DefaultRouter()
# Registrar el conjunto de vistas para los datos del sensor
# Endpoints registrados:
# - GET /api/sensor-data/ : Obtener lista de datos del sensor
# - POST /api/sensor-data/ : Crear un nuevo registro de datos del sensor
# - GET /api/sensor-data/{id}/ : Obtener un registro específico de datos del sensor
# - PUT /api/sensor-data/{id}/ : Actualizar un registro específico de datos del sensor
# - PATCH /api/sensor-data/{id}/ : Actualizar parcialmente un registro específico de datos del sensor
# - DELETE /api/sensor-data/{id}/ : Eliminar un registro específico de datos del sensor
# - GET /api/sensor-data/latest/ : Obtener los últimos datos del sensor
router.register(r'api/sensor-data', SensorDataViewSet, basename='sensor-data')

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('charts/', ChartsView.as_view(), name='charts'),
    path('chart/', ChartView.as_view(), name='chart'),
    path('dual-chart/', DualChartView.as_view(), name='dual-chart'),
    path('gauges/', GaugesView.as_view(), name='gauges'),
    path('table-coef/', TableCoefView.as_view(), name='table-coef'),
    path('development/', DevelopmentView.as_view(), name='development'),
    path('old-devices/', OldDevicesChartView.as_view(), name='old-devices'),
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)