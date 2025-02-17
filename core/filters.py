from django.db.models import QuerySet
from django_filters import rest_framework as filters
from .models import DataPoint

class DataPointFilter(filters.FilterSet):
    timestamp_after = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    class Meta:
        model = DataPoint
        fields = {
            'sensor': ['exact'],
            'metric': ['exact', 'contains'],
            'value': ['gt', 'lt', 'exact'],
        }

    def filter_queryset(self, queryset: QuerySet[DataPoint]) -> QuerySet[DataPoint]:
        return super().filter_queryset(queryset)