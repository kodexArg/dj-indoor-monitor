from typing import Optional
from django.db.models import QuerySet
from django_filters import rest_framework as filters
from .models import SensorData

class SensorDataFilter(filters.FilterSet):
    """
    FilterSet para el modelo SensorData. Permite filtrar datos de sensores según varios criterios.

    Parámetros de filtro:
    - `timestamp_after` (datetime): Filtra datos después de esta marca de tiempo
    - `timestamp_before` (datetime): Filtra datos antes de esta marca de tiempo
    - `sensor` (str): Identificador del sensor
    - `t` (float): Temperatura
    - `h` (float): Humedad

    Ejemplos de consultas:
    - `?timestamp_after=2023-12-01T00:00:00Z`
    - `?t__gt=25&t__lt=30`
    - `?h__gt=40&h__lt=60`
    - `?sensor=sensor1&h=45`
    - `?sensor__contains=living`
    """
    timestamp_after = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    class Meta:
        model = SensorData
        fields = {
            'sensor': ['exact', 'contains'],
            't': ['gt', 'lt', 'exact'],
            'h': ['gt', 'lt', 'exact'],
        }

    def filter_queryset(self, queryset: QuerySet[SensorData]) -> QuerySet[SensorData]:
        """Filtra el conjunto de datos basado en los parámetros de consulta."""
        return super().filter_queryset(queryset)