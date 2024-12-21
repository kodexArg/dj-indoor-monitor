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
    - `limit` (int): Número máximo de registros (default: 200)
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
    limit = filters.NumberFilter(method='filter_limit')
    
    class Meta:
        model = SensorData
        fields = {
            'sensor': ['exact', 'contains'],
            't': ['gt', 'lt', 'exact'],
            'h': ['gt', 'lt', 'exact'],
        }

    def filter_queryset(self, queryset: QuerySet[SensorData]) -> QuerySet[SensorData]:
        """Filtra el conjunto de datos basado en los parámetros de consulta."""
        queryset = super().filter_queryset(queryset)
        if not any([
            self.data.get('timestamp_after'),
            self.data.get('timestamp_before'),
            self.data.get('limit')
        ]):
            return queryset[:200]  # Límite por defecto
        return queryset

    def filter_limit(self, queryset: QuerySet[SensorData], name: str, value: Optional[int]) -> QuerySet[SensorData]:
        """Aplica un límite al número de registros devueltos."""
        try:
            return queryset[:int(value)]
        except (ValueError, TypeError):
            return queryset[:2000]