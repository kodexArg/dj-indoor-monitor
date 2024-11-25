# Python imports
from datetime import datetime, timedelta, timezone
import json
import requests
import pandas as pd

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
from .utils import parse_time_string, generate_plotly_chart, timeframe_to_freq, get_start_date


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
        metric = request.query_params.get('metric', 't')
        timeframe = request.query_params.get('timeframe', '30m')
        freq = timeframe_to_freq(timeframe)
        
        if metric not in ['t', 'h']:
            return Response(
                {'error': "metric must be either 't' for temperature or 'h' for humidity"},
                status=400
            )

        # Usar get_start_date para filtrar
        end_date = datetime.now(timezone.utc)
        start_date = get_start_date(freq, end_date)
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                timestamp__gte=start_date,
                timestamp__lte=end_date
            )
        )

        # Convert to DataFrame for processing
        df = pd.DataFrame(queryset.values('timestamp', 'sensor', metric))
        
        if df.empty:
            return Response({'data': []})

        # Process data
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Group and aggregate
        grouped = df.groupby([
            'sensor',
            pd.Grouper(key='timestamp', freq=freq)
        ]).agg({
            metric: 'mean'
        }).reset_index()
        
        # Format output
        grouped['timestamp'] = grouped['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
        grouped[metric] = grouped[metric].round(1)
        
        # Sort and limit records
        grouped = grouped.sort_values(['timestamp', 'sensor'], ascending=[False, True])
        grouped = grouped.tail(settings.MAX_PLOT_RECORDS)
        
        return Response({'data': grouped.to_dict('records')})


# Template Views
class HomeView(TemplateView):
    template_name = 'home.html'


class DevelopmentView(TemplateView):
    template_name = 'development.html'


class ChartView(TemplateView):
    template_name = 'chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get parameters with defaults
        metric = self.request.GET.get('metric', 't')
        selected_timeframe = self.request.GET.get('timeframe', '30m')
        freq = timeframe_to_freq(selected_timeframe)
        
        # Build API URL and get data
        api_url = self.request.build_absolute_uri(reverse('sensor-data-chart'))
        params = {'metric': metric, 'timeframe': selected_timeframe}
        
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # Generate chart
        chart_html = generate_plotly_chart(data['data'], metric)
        
        context.update({
            'chart_html': chart_html,
            'metric': metric,
            'selected_timeframe': selected_timeframe,
            'api_url': api_url,
            'data': data['data']
        })
            
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

