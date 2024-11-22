from django_filters import rest_framework as filters
from .models import SensorData

class SensorDataFilter(filters.FilterSet):
    """
    FilterSet for SensorData model.
    
    Filter Parameters:
        timestamp_after (datetime): Filter data after this timestamp (inclusive)
        timestamp_before (datetime): Filter data before this timestamp (inclusive)
        sensor (str): Filter by sensor identifier with following operations:
            - sensor: Exact match
            - sensor__contains: Partial match (case-sensitive)
        t (float): Filter by temperature with following operations:
            - t: Exact match
            - t__gt: Greater than
            - t__lt: Less than
        h (float): Filter by humidity with following operations:
            - h: Exact match
            - h__gt: Greater than
            - h__lt: Less than
            
    Example Queries:
        ?timestamp_after=2023-12-01T00:00:00Z
        ?t__gt=25&t__lt=30
        ?h__gt=40&h__lt=60
        ?sensor=sensor1&h=45
        ?sensor__contains=living
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