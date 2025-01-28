from typing import Optional
from django.db.models import QuerySet
from django_filters import rest_framework as filters
from .models import SensorData, SensorDataLegacy

class SensorDataFilter(filters.FilterSet):
    timestamp_after = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    class Meta:
        model = SensorData
        fields = {
            'sensor': ['exact', 'contains'],
            't': ['gt', 'lt', 'exact'],
            'h': ['gt', 'lt', 'exact'],
            's': ['gt', 'lt', 'exact'],
            'l': ['gt', 'lt', 'exact'],
            'r': ['gt', 'lt', 'exact'],
        }

    def filter_queryset(self, queryset: QuerySet[SensorData]) -> QuerySet[SensorData]:
        return super().filter_queryset(queryset)

class SensorDataLegacyFilter(SensorDataFilter):
    class Meta:
        model = SensorDataLegacy
        fields = {
            'sensor': ['exact', 'contains'],
            't': ['gt', 'lt', 'exact'],
            'h': ['gt', 'lt', 'exact'],
        }