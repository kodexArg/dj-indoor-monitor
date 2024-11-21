# Python
from datetime import datetime, timedelta, timezone
import json
import requests

# Django and DRF
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import localtime
from django.urls import reverse
from django.template import loader
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView
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
    
    Examples:
    - Fetch all records from the Raspberry Pi "rpi02":
      `/api/sensor-data/?rpi=rpi02`
    
    - Fetch all records from the Raspberry Pi "rpi05" from the last minute:
      `/api/sensor-data/?rpi=rpi05&seconds=60`
    
    - Fetch all records from the last 30 seconds:
      `/api/sensor-data/?seconds=30`
    
    - Fetch all records from April 1st to April 4th:
      `/api/sensor-data/?start_date=2023-04-01&end_date=2023-04-04`
    """
    serializer_class = SensorDataSerializer
    filterset_class = SensorDataFilter

    def get_queryset(self):
        max_time_threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.MAX_DATA_MINUTES)
        seconds = self.request.query_params.get('seconds', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if seconds is not None and seconds.isdigit():
            seconds = int(seconds)
            since = datetime.now(timezone.utc) - timedelta(seconds=seconds)
            max_time_threshold = max(max_time_threshold, since)
        
        if start_date and end_date:
            start_date = datetime.fromisoformat(start_date)
            end_date = datetime.fromisoformat(end_date)
            queryset = SensorData.objects.filter(timestamp__range=(start_date, end_date))
        else:
            queryset = SensorData.objects.filter(timestamp__gte=max_time_threshold)
        
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        serializer.save()
        timestamp = localtime(serializer.instance.timestamp).strftime('%H:%M:%S')
        # logger.debug(f"S: {timestamp} ✅")


class ChartDataListView(ListAPIView):
    serializer_class = SensorDataSerializer

    def _fetch_from_api(self, params=None):
        api_url = self.request.build_absolute_uri(reverse('sensor-data-list'))
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            return response.json()
        return []

    def list(self, request, *args, **kwargs):
        start_time = datetime.now(timezone.utc)
        
        # Prepare parameters
        params = {}
        if request.query_params.get('recent', 'false').lower() == 'true':
            params['seconds'] = 5
        for param in ['seconds', 'start_date', 'end_date']:
            if value := request.query_params.get(param):
                params[param] = value
        
        # Fetch and process data
        data = self._fetch_from_api(params)
        metric = request.query_params.get('metric', 't')  # default to temperature
        freq = request.query_params.get('freq', '3s')    # allow custom frequency
        result = process_chart_data(data, metric=metric, freq=freq)
        
        end_time = datetime.now(timezone.utc)
        result['latency'] = (end_time - start_time).total_seconds()
        
        return Response(result)


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

