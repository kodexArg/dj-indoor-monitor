from django.db.models import QuerySet, Q
from django_filters import rest_framework as filters
from typing import List, Dict, Any
from .models import DataPoint


class MetricRangeFilter(filters.NumberFilter):
    """Filtro numérico para rangos de métricas según tipo y rangos válidos predefinidos."""
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
        
        # Aplicar filtro de rango para la métrica específica
        return qs.filter(
            Q(metric=self.metric_type) & 
            Q(value__gte=ranges['min']) & 
            Q(value__lte=ranges['max'])
        )


class DataPointFilter(filters.FilterSet):
    """Conjunto de filtros para DataPoint: rangos de fecha, sensores, rangos de valor por métrica y opción de último valor."""
    VALID_RANGES = { # Rangos de valores aceptables por métrica
        't': {'min': 2, 'max': 70},
        'h': {'min': 2, 'max': 100},
        's': {'min': 2, 'max': 99}
    }
    
    timestamp_after = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    start_date = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    sensors = filters.CharFilter(method='filter_sensors')
    
    temperature_range = MetricRangeFilter(metric_type='t', valid_ranges=VALID_RANGES)
    humidity_range = MetricRangeFilter(metric_type='h', valid_ranges=VALID_RANGES)
    state_range = MetricRangeFilter(metric_type='s', valid_ranges=VALID_RANGES)
    
    latest_only = filters.BooleanFilter(method='filter_latest_only')
    
    class Meta:
        model = DataPoint
        fields = {
            'sensor': ['exact'],
            'metric': ['exact', 'contains'],
            'value': ['gt', 'lt', 'exact'],
        }
    
    def filter_sensors(self, queryset, name, value):
        """Filtra queryset por lista de sensores (string separado por comas)."""
        if not value:
            return queryset
        
        sensor_list = [s.strip() for s in value.split(',')]
        return queryset.filter(sensor__in=sensor_list)

    def filter_latest_only(self, queryset, name, value):
        """Filtra queryset para devolver solo el DataPoint más reciente por sensor si 'value' es True."""
        if value:
            # Ordena y toma el primer valor (más reciente) para cada sensor.
            return queryset.order_by('sensor', '-timestamp').distinct('sensor')
        return queryset

    def filter_queryset(self, queryset: QuerySet[DataPoint]) -> QuerySet[DataPoint]:
        """Aplica validaciones generales de rango de métricas si no hay filtros específicos de rango activos."""
        queryset = super().filter_queryset(queryset)
        
        # Aplicar validación de rango general si no se usó un filtro de rango específico.
        if not any(param in self.form.data for param in 
                  ['temperature_range', 'humidity_range', 'state_range']):
            queryset = self.apply_metric_ranges(queryset)
            
        return queryset
    
    def apply_metric_ranges(self, queryset: QuerySet) -> QuerySet:
        """Aplica rangos de valor válidos para métricas conocidas ('t', 'h', 's') mediante un objeto Q."""
        metric_filter = Q()
        
        # Construir Q object para todos los rangos de métricas válidas.
        for metric, ranges in self.VALID_RANGES.items():
            metric_filter |= (
                Q(metric=metric) & 
                Q(value__gte=ranges['min']) & 
                Q(value__lte=ranges['max'])
            )
        
        # Permitir métricas no definidas en VALID_RANGES (sin filtro de rango para ellas).
        defined_metrics = list(self.VALID_RANGES.keys())
        metric_filter |= ~Q(metric__in=defined_metrics)
        
        return queryset.filter(metric_filter)