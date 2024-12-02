# Python
from datetime import datetime, timedelta, timezone

# Django y DRF
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# Local
from .models import SensorData
from .serializers import SensorDataSerializer
from .filters import SensorDataFilter
from .utils import generate_plotly_chart, get_start_date


class SensorDataViewSet(viewsets.ModelViewSet):
    """
    Parámetros:
    - `seconds`: Opcional. Número de segundos para obtener datos. No excederá `max_time_threshold`.
    - `start_date` y `end_date`: Opcional. Rango de fechas para obtener datos.
    - `metric`: Opcional. Métrica a obtener (ej: 't' para temperatura). Por defecto 't'.
    - `freq`: Opcional. Frecuencia para agregar datos (ej: '30s'). Por defecto '30s'.
    
    Ejemplos:
    - Obtener registros del sensor "sensor02":
      `/api/sensor-data/?sensor=sensor02`
    
    - Obtener registros del sensor "sensor05" del último minuto:
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

    @action(detail=False, methods=['post'])
    def write_values(self, request):
        sensor_data = request.data
        sensor_data['timestamp'] = parse_datetime(sensor_data['timestamp'])
        serializer = SensorDataSerializer(data=sensor_data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'Values written successfully'}, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        # Get and validate parameters
        timestamp_param = request.query_params.get('timestamp')
        metric = request.query_params.get('metric')
        
        # Validate metric first since it can trigger early return
        valid_metrics = ['t', 'h']
        if metric and metric not in valid_metrics:
            return Response(
                {'error': f'Invalid metric. Use one of: {", ".join(valid_metrics)}'},
                status=400
            )
        
        # Handle timestamp
        if timestamp_param:
            since = datetime.fromisoformat(timestamp_param)
        else:
            since = self.now() - timedelta(seconds=5)
        
        # Query data
        queryset = SensorData.objects.filter(timestamp__gte=since)
        
        # Select fields based on metric
        fields = ['timestamp', 'sensor']
        if metric:
            fields.append(metric)
        else:
            fields.extend(['t', 'h'])
        
        # Format response
        data = list(queryset.values(*fields))
        for item in data:
            item['timestamp'] = item['timestamp'].isoformat()
        
        return Response(data)

class HomeView(TemplateView):
    """Vista principal de la aplicación"""
    template_name = 'home.html'

class DevelopmentView(TemplateView):
    """Vista de desarrollo para pruebas"""
    template_name = 'development.html'

@method_decorator(cache_page(60 * 15), name='dispatch')
class ChartView(TemplateView):
    """Vista para mostrar gráficos de datos de sensores"""
    template_name = 'chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        selected_timeframe = self.request.GET.get('timeframe', '30min')
        metric = self.request.GET.get('metric', 't')
        
        end_date = datetime.now(timezone.utc) 
        start_date = get_start_date(selected_timeframe, end_date)
        
        queryset = SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')  # Ordenar cronológicamente
        
        data = list(queryset.values('timestamp', 'sensor', metric))

        chart_html, plotted_points = generate_plotly_chart(data, metric, start_date, end_date, selected_timeframe)
        
        debug_info = {
            'num_points': len(data),
            'plotted_points': plotted_points,
            'sensors': sorted(set(item['sensor'] for item in data)),
            'first_record': {
                'timestamp': data[0]['timestamp'] if data else None,
                'sensor': data[0]['sensor'] if data else None,
                'value': data[0][metric] if data else None
            },
            'last_record': {
                'timestamp': data[-1]['timestamp'] if data else None,
                'sensor': data[-1]['sensor'] if data else None,
                'value': data[-1][metric] if data else None
            },
            'first_record_online': {
                'timestamp': data[1]['timestamp'] if len(data) > 1 else None,
                'sensor': data[1]['sensor'] if len(data) > 1 else None,
                'value': data[1][metric] if len(data) > 1 else None
            },
            'second_record_online': {
                'timestamp': data[2]['timestamp'] if len(data) > 2 else None,
                'sensor': data[2]['sensor'] if len(data) > 2 else None,
                'value': data[2][metric] if len(data) > 2 else None
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
        
        return context


def fetch_data(request, sensor=None, seconds=None):
    queryset = SensorData.objects.all().order_by('-timestamp')
    
    if seconds:
        since = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        queryset = queryset.filter(timestamp__gte=since)
    
    if sensor:
        queryset = queryset.filter(sensor=sensor)
    
    return list(queryset.values())

def latest_data_table(request):
    data = fetch_data(request, seconds=settings.MAX_DATA_MINUTES * 60)
    return render(request, 'partials/latest-data-table-rows.html', {'data': data})

