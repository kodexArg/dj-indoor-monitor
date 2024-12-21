# Django y DRF
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
    ChartView,
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
    path('development/', DevelopmentView.as_view(), name='development'),
    path('chart/', ChartView.as_view(), name='chart'),
    path('old-devices/', OldDevicesChartView.as_view(), name='old-devices'),
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)