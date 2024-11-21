# Python
from datetime import datetime, timedelta, timezone
import json
import requests

# Django and DRF
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils.timezone import localtime
from django.urls import reverse
from rest_framework import viewsets
from rest_framework.decorators import action

from rest_framework.response import Response
from django_filters import rest_framework as filters

# Third-party
from loguru import logger

# Local
from .models import SensorData
from .serializers import SensorDataSerializer
from .filters import SensorDataFilter
from .utils import process_chart_data

# Template Views
class HomeView(TemplateView):
    template_name = 'home.html'
    
class DevelopmentView(TemplateView):
    template_name = 'development.html'

class ChartView(TemplateView):
    template_name = 'chart.html'


# ViewSets
class SensorDataViewSet(viewsets.ModelViewSet):
    """
    A viewset that provides the standard actions for SensorData.
    
    Query Parameters:
    - `seconds`: Optional. The number of seconds to fetch data for. The data returned will not exceed the `max_time_threshold`.
    - `start_date` and `end_date`: Optional. Date range to fetch data for.
    - `metric`: Optional. The metric to fetch data for (e.g., 't' for temperature). Default is 't'.
    - `freq`: Optional. The frequency for aggregating data (e.g., '30s' for 30 seconds). Default is '30s'.
    
    Examples:
    - Fetch all records from the Raspberry Pi "rpi02":
      `/api/sensor-data/?rpi=rpi02`
    
    - Fetch all records from the Raspberry Pi "rpi05" from the last minute:
      `/api/sensor-data/?rpi=rpi05&seconds=60`
    
    - Fetch all records from April 1st to April 4th:
      `/api/sensor-data/?start_date=2023-04-01&end_date=2023-04-04`
    
    - Fetch chart data for temperature with 1-minute frequency:
      `/api/sensor-data/?metric=t&freq=1m`
    """
    serializer_class = SensorDataSerializer
    filterset_class = SensorDataFilter

    def get_queryset(self):
        max_time_threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.MAX_DATA_MINUTES)
        seconds = self.request.query_params.get('seconds', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        queryset = SensorData.objects.all()
        
        if seconds:
            seconds = int(seconds)
            since = max(
                max_time_threshold,
                datetime.now(timezone.utc) - timedelta(seconds=seconds)
            )
            queryset = queryset.filter(timestamp__gte=since)
        
        if start_date:
            start_date = datetime.fromisoformat(start_date)
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            end_date = datetime.fromisoformat(end_date)
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset.order_by('-timestamp')

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Custom action to fetch recent sensor data.
        endpoint: /api/sensor-data/recent/
        """
        queryset = self.get_queryset().filter(timestamp__gte=datetime.now(timezone.utc) - timedelta(seconds=30))
        metric = request.query_params.get('metric', 't')
        freq = request.query_params.get('freq', '30s')
        data = queryset.values('timestamp', 'rpi', metric)
        processed_data = process_chart_data(list(data), metric=metric, freq=freq)
        return Response(processed_data)

    @action(detail=False, methods=['get'])
    def chart_data(self, request):
        """
        Custom action to fetch data formatted for charts.
        """
        queryset = self.filter_queryset(self.get_queryset())
        metric = request.query_params.get('metric', 't')
        freq = request.query_params.get('freq', '30s')
        data = queryset.values('timestamp', 'rpi', metric)
        processed_data = process_chart_data(list(data), metric=metric, freq=freq)
        return Response(processed_data)



# Function-based Views
def fetch_data(request, rpi=None, seconds=None):
    api_url = request.build_absolute_uri(reverse('sensor-data-list'))
    params = {}
    if seconds:
        params['seconds'] = seconds
    if rpi:
        params['rpi'] = rpi
    response = requests.get(api_url, params=params)
    data = response.json()
    for item in data:
        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
    return data

def latest_data_table(request):
    data = fetch_data(request)
    return render(request, 'partials/latest-data-table-rows.html', {'data': data})

