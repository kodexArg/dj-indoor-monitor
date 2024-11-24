# Python imports
from datetime import datetime, timedelta, timezone
import json
import requests

# Django and DRF
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView
from django.urls import reverse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters

# Third-party
from loguru import logger
from plotly.io import to_html

# Local
from .models import SensorData
from .serializers import SensorDataSerializer
from .filters import SensorDataFilter
from .utils import process_chart_data, parse_time_string, generate_plotly_chart


# Main Project ViewSets (keep at top)
class SensorDataViewSet(viewsets.ModelViewSet):
    """
    A viewset that provides the standard actions for SensorData.
    
    Query Parameters:
    - `seconds`: Optional. The number of seconds to fetch data for. The data returned will not exceed the `max_time_threshold`.
    - `start_date` and `end_date`: Optional. Date range to fetch data for.
    - `metric`: Optional. The metric to fetch data for (e.g., 't' for temperature). Default is 't'.
    - `freq`: Optional. The frequency for aggregating data (e.g., '30s' for 30 seconds). Default is '30s'.
    
    Examples:
    - Fetch all records from sensor "sensor02":
      `/api/sensor-data/?sensor=sensor02`
    
    - Fetch all records from sensor "sensor05" from the last minute:
      `/api/sensor-data/?sensor=sensor05&seconds=60`
    """
    serializer_class = SensorDataSerializer
    filterset_class = SensorDataFilter

    @classmethod
    def now(cls):
        return datetime.now(timezone.utc)

    def get_queryset(self):
        max_time_threshold = self.now() - timedelta(minutes=settings.MAX_DATA_MINUTES)
        seconds = self.request.query_params.get('seconds', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        queryset = SensorData.objects.all()

        if seconds:
            seconds = int(seconds)
            since = max(
                max_time_threshold,
                self.now() - timedelta(seconds=seconds)
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
    def chart(self, request):
        recent = request.query_params.get('recent', 'false').lower() == 'true'
        metric = request.query_params.get('metric', 't')
        freq = request.query_params.get('freq', '30s')

        if recent:
            seconds = parse_time_string(freq)
            queryset = self.get_queryset().filter(
                timestamp__gte=self.now() - timedelta(seconds=seconds)
            )
        else:
            queryset = self.filter_queryset(self.get_queryset())

        data = queryset.values('timestamp', 'sensor', metric)
        processed_data = process_chart_data(list(data), metric=metric, freq=freq)
        return Response(processed_data)


# Template Views
class HomeView(TemplateView):
    template_name = 'home.html'


class DevelopmentView(TemplateView):
    template_name = 'development.html'


class ChartView(TemplateView):
    template_name = 'chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metric = self.request.GET.get('metric', 't')
        selected_timeframe = self.request.GET.get('timeframe', '30m')
        
        # Actualizar mapeo usando 'T' para minutos
        timeframe_to_freq = {
            '5s': '5s',
            '30s': '30s',
            '1m': '1T',
            '10m': '10T',
            '30m': '30T',
            '1h': '1H',
            '1d': '1D'
        }
        freq = timeframe_to_freq.get(selected_timeframe, '30T')
        
        # Log the selected metric and timeframe
        logger.info(f"Selected metric: {metric}")
        logger.info(f"Selected timeframe: {selected_timeframe}")
        
        # Construir URL de la API
        api_url = self.request.build_absolute_uri(reverse('sensor-data-chart'))
        params = {'metric': metric, 'freq': freq}
        
        # Obtener datos de la API
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # Generar gráfico
        chart_html = generate_plotly_chart(data['data'], metric)
        context['chart_html'] = chart_html

        context['metric'] = metric
        context['freq'] = freq
        context['api_url'] = api_url
        context['params'] = params
        context['api_response'] = data

        if data['data']:
            context['start_date'] = data['data'][0]['timestamp']
            context['end_date'] = data['data'][-1]['timestamp']
            context['num_points'] = len(data['data'])
        else:
            context['start_date'] = context['end_date'] = context['num_points'] = None

        # Add selected_timeframe to context
        context['selected_timeframe'] = selected_timeframe
        
        return context


# Function-based Views
def fetch_data(request, sensor=None, seconds=None):
    api_url = request.build_absolute_uri(reverse('sensor-data-list'))
    params = {}
    if seconds:
        params['seconds'] = seconds
 
    if sensor:
        params['sensor'] = sensor
    response = requests.get(api_url, params=params)
    data = response.json()
    for item in data:
        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
    return data


def latest_data_table(request):
    data = fetch_data(request)
    return render(request, 'partials/latest-data-table-rows.html', {'data': data})

