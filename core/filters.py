from django.db.models import QuerySet, Q
from django_filters import rest_framework as filters
from typing import List, Dict, Any
from .models import DataPoint


class MetricRangeFilter(filters.NumberFilter):
    """Filtro personalizado para manejar rangos de métricas por tipo"""
    
    def __init__(self, *args, **kwargs):
        self.metric_type = kwargs.pop('metric_type', None)
        self.valid_ranges = kwargs.pop('valid_ranges', {})
        super().__init__(*args, **kwargs)
    
    def filter(self, qs, value):
        if value is None:
            return qs
        
        if not self.metric_type or self.metric_type not in self.valid_ranges:
            return qs
        
        ranges = self.valid_ranges[self.metric_type]
        
        # Aplicar el rango específico para este tipo de métrica
        return qs.filter(
            Q(metric=self.metric_type) & 
            Q(value__gte=ranges['min']) & 
            Q(value__lte=ranges['max'])
        )


class DataPointFilter(filters.FilterSet):
    """
    Filtro para DataPoint con soporte para:
    - Rangos de fechas (timestamp_after, timestamp_before)
    - Filtrado por sensor (sensor, sensors)
    - Filtrado por métrica con validación de rangos
    """
    # Rangos válidos para diferentes métricas
    VALID_RANGES = {
        't': {'min': 2, 'max': 70},
        'h': {'min': 2, 'max': 100},
        's': {'min': 2, 'max': 99}
    }
    
    # Filtros de timestamp
    timestamp_after = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    # Alias para start_date y end_date
    start_date = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    # Filtro para lista de sensores
    sensors = filters.CharFilter(method='filter_sensors')
    
    # Filtros de rango por tipo de métrica
    temperature_range = MetricRangeFilter(metric_type='t', valid_ranges=VALID_RANGES)
    humidity_range = MetricRangeFilter(metric_type='h', valid_ranges=VALID_RANGES)
    state_range = MetricRangeFilter(metric_type='s', valid_ranges=VALID_RANGES)
    
    class Meta:
        model = DataPoint
        fields = {
            'sensor': ['exact'],
            'metric': ['exact', 'contains'],
            'value': ['gt', 'lt', 'exact'],
        }
    
    def filter_sensors(self, queryset, name, value):
        """Filtra por múltiples sensores si se proporciona una lista separada por comas"""
        if not value:
            return queryset
        
        sensor_list = [s.strip() for s in value.split(',')]
        return queryset.filter(sensor__in=sensor_list)

    def filter_queryset(self, queryset: QuerySet[DataPoint]) -> QuerySet[DataPoint]:
        """
        Aplica todos los filtros y además aplica la validación de rangos de métricas
        para asegurar que los valores estén dentro de rangos aceptables
        """
        queryset = super().filter_queryset(queryset)
        
        # Si no se han aplicado filtros de rango específicos, aplicamos el filtro general
        if not any(param in self.form.data for param in 
                  ['temperature_range', 'humidity_range', 'state_range']):
            queryset = self.apply_metric_ranges(queryset)
            
        return queryset
    
    def apply_metric_ranges(self, queryset: QuerySet) -> QuerySet:
        """
        Aplica filtros de rango para todas las métricas en una sola consulta eficiente
        """
        metric_filter = Q()
        
        # Construir un solo Q object para todos los rangos de métricas
        for metric, ranges in self.VALID_RANGES.items():
            metric_filter |= (
                Q(metric=metric) & 
                Q(value__gte=ranges['min']) & 
                Q(value__lte=ranges['max'])
            )
        
        # Añadir filtro para métricas que no están en VALID_RANGES
        defined_metrics = list(self.VALID_RANGES.keys())
        metric_filter |= ~Q(metric__in=defined_metrics)
        
        return queryset.filter(metric_filter)