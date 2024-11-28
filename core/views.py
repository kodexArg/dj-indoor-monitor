# Python imports
from datetime import datetime, timedelta, timezone
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
from django.utils.dateparse import parse_datetime

# Third-party
from loguru import logger

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
        
        queryset = SensorData.objects.all().order_by('-timestamp')

        if seconds:
            seconds = int(seconds)
            since = max(
                max_time_threshold,
                self.now() - timedelta(seconds=seconds)
            )
            queryset = queryset.filter(timestamp__gte=since)
        
        if start_date:
            start_date = datetime.fromisoformat(start_date)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            queryset = queryset.filter(timestamp__gte=start_date)

        if end_date:
            end_date = datetime.fromisoformat(end_date)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset.order_by('-timestamp')

    @action(detail=False, methods=['get'])
    def chart(self, request):
        metric = request.query_params.get('metric', 't')
        timeframe = request.query_params.get('timeframe', '30s')
        freq = timeframe_to_freq(timeframe)
        start_date = datetime.fromisoformat(request.query_params['start_date'])
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        end_date = datetime.fromisoformat(request.query_params['end_date'])
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                timestamp__gte=start_date,
                timestamp__lte=end_date
            )
        )

        df = pd.DataFrame(queryset.values('timestamp', 'sensor', metric))
        if df.empty:
            return Response({'data': []})

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        logger.debug(f"total records before resampling: {len(df)}, freq={freq}")

        # Filter for sensor 'flora-01'
        df = df[df['sensor'] == 'flora-01']
        
        # Ensure timestamps are exactly aligned to 5s intervals
        df.index = df.index.floor('5s')
        
        logger.debug(f"Data after filtering:\n{df}")

        # Group and resample with fill method
        resampled = (df.groupby('sensor')
                     .resample(freq, origin='start')  # Add origin parameter
                     .mean()
                     .ffill()  # Forward fill missing values
                     .reset_index())

        logger.debug(f"Resampled data:\n{resampled}")


        # Validation
        original_count = len(df)
        resampled_count = len(resampled)
        if freq == '5S' and original_count != resampled_count:
            logger.warning(f"Data point count mismatch: original={original_count}, resampled={resampled_count}")

        logger.debug(f"total records after resampling: {len(resampled)}, freq={freq}")
        
        resampled[metric] = resampled[metric].round(1)
        
        resampled = resampled.sort_values(['timestamp'], ascending=[False])
        
        return Response({'data': resampled.to_dict('records')})

    @action(detail=False, methods=['post'])
    def write_values(self, request):
        sensor_data = request.data
        sensor_data['timestamp'] = parse_datetime(sensor_data['timestamp'])
        serializer = SensorDataSerializer(data=sensor_data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'Values written successfully'}, status=201)
        return Response(serializer.errors, status=400)


# Template Views
class HomeView(TemplateView):
    template_name = 'home.html'

class DevelopmentView(TemplateView):
    template_name = 'development.html'


class ChartView(TemplateView):
    template_name = 'chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        selected_timeframe = self.request.GET.get('timeframe', '30s')
        metric = self.request.GET.get('metric', 't')
        
        freq = timeframe_to_freq(selected_timeframe)
        end_date = datetime.now()
        start_date = get_start_date(freq, end_date)
        logger.debug(f"Start date, iso format: {start_date.isoformat()}")
        
        # Build API URL and get data
        api_url = self.request.build_absolute_uri(reverse('sensor-data-chart'))
        params = {
            'metric': metric,
            'timeframe': selected_timeframe,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()  # Lanzará una excepción si el status code no es 2XX
            data = response.json()['data']
            
            # Generate chart
            chart_html = generate_plotly_chart(data, metric, start_date, end_date)
            
            # Prepare debug info
            debug_info = {
                'num_points': len(data),
                'sensors': sorted(set(item['sensor'] for item in data)),
                'first_record': {
                    'timestamp': data[-1]['timestamp'] if data else None,
                    'sensor': data[-1]['sensor'] if data else None,
                    'value': data[-1][metric] if data else None
                },
                'last_record': {
                    'timestamp': data[0]['timestamp'] if data else None,
                    'sensor': data[0]['sensor'] if data else None,
                    'value': data[0][metric] if data else None
                }
            }
            
            context.update({
                'chart_html': chart_html,
                'start_date': start_date,
                'end_date': end_date,
                'selected_timeframe': selected_timeframe,
                'metric': metric,
                'debug': debug_info
            })
        except requests.RequestException as e:
            context.update({'error': str(e)})
        
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

