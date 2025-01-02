from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from django.db.models import QuerySet

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
from .utils import generate_plotly_chart, get_start_date, generate_simple_plotly_chart, generate_dual_plotly_chart, generate_gauges


class SensorDataViewSet(viewsets.ModelViewSet):
    """
    Vista para gestionar los datos de los sensores. Permite obtener, filtrar y escribir datos.

    Parámetros:
    - `seconds`: Opcional. Número de segundos para obtener datos. No excederá `max_time_threshold`.
    - `start_date` y `end_date`: Opcional. Rango de fechas para obtener datos.
    - `metric`: Opcional. Métrica a obtener (ej: 't' para temperatura). Por defecto 't'.
    - `freq`: Opcional. Frecuencia para agregar datos (ej: '30s'). Por defecto '30s'.
    
    Ejemplos:
    - Obtener registros del sensor "sensor02": `/api/sensor-data/?sensor=sensor02`
    - Obtener registros del sensor "sensor05" del último minuto: `/api/sensor-data/?sensor=sensor05&seconds=60`
    """
    serializer_class = SensorDataSerializer
    filterset_class = SensorDataFilter

    def get_queryset(self) -> QuerySet[SensorData]:
        """
        Obtiene el conjunto de datos del sensor basado en los parámetros de consulta.

        Parámetros:
        - `seconds`: Opcional. Número de segundos para obtener datos.
        - `start_date` y `end_date`: Opcional. Rango de fechas para obtener datos.

        Ejemplos:
        - Obtener registros del sensor "sensor02": `/api/sensor-data/?sensor=sensor02`
        """
        max_time_threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.MAX_DATA_MINUTES)
        seconds = self.request.query_params.get('seconds', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        queryset = SensorData.objects.all().order_by('-timestamp')

        if not any([seconds, start_date, end_date]):
            return queryset[:settings.DEFAULT_QUERY_LIMIT]

        if seconds:
            seconds = int(seconds)
            since = max(
                max_time_threshold,
                datetime.now(timezone.utc) - timedelta(seconds=seconds)
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
    def latest(self, request) -> Response:
        """
        Obtiene el último valor de cada sensor.
        """
        metric = request.query_params.get('metric')
        valid_metrics = ['t', 'h']
        if metric and metric not in valid_metrics:
            return Response(
                {'error': f'Invalid metric. Use one of: {", ".join(valid_metrics)}'},
                status=400
            )

        since = datetime.now(timezone.utc) - timedelta(minutes=60)  # último hora
        base_queryset = SensorData.objects.filter(timestamp__gte=since)
        
        latest_data = []
        sensors = base_queryset.values_list('sensor', flat=True).distinct()
        
        for sensor in sensors:
            latest_record = base_queryset.filter(sensor=sensor).order_by('-timestamp').first()
            if latest_record:
                sensor_data = {
                    'timestamp': latest_record.timestamp.isoformat(),
                    'sensor': latest_record.sensor,
                }
                
                if metric:
                    sensor_data[metric] = getattr(latest_record, metric)
                else:
                    sensor_data['t'] = latest_record.t
                    sensor_data['h'] = latest_record.h
                    
                latest_data.append(sensor_data)

        return Response(latest_data)

class HomeView(TemplateView):
    """Vista principal de la aplicación"""
    template_name = 'home.html'

class DevelopmentView(TemplateView):
    """Vista de desarrollo para pruebas"""
    template_name = 'development.html'

@method_decorator(cache_page(60 * 15), name='dispatch')
class ChartView(TemplateView):
    """Vista para mostrar gráficos de datos de sensores"""
    template_name = 'partials/charts/chart.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Obtiene el contexto para la vista de gráficos.

        Parámetros:
        - `kwargs`: Argumentos adicionales.

        Ejemplos:
        - Ver gráfico de temperatura: `/chart/?metric=t`
        """
        context = super().get_context_data(**kwargs)
        
        selected_timeframe = self.request.GET.get('timeframe', '30min')
        metric = self.request.GET.get('metric', 't')
        
        end_date = datetime.now(timezone.utc)
        start_date = get_start_date(selected_timeframe, end_date)
        
        queryset = SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
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

class GaugesView(TemplateView):
    template_name = 'partials/charts/gauges.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(minutes=10)

        data = list(SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('sensor').distinct())

        sensors = sorted(item['sensor'] for item in data)
        context.update({
            'sensors': sensors,
            'metrics': ['t', 'h']
        })
        return context

class DualChartView(TemplateView):
    template_name = 'partials/charts/dual-chart.html'


class TableCoefView(TemplateView):
    template_name = 'partials/charts/table-coef.html'

from django.views.generic import TemplateView

class ChartsView(TemplateView):
    """
    Vista que agrupa varios gráficos disponibles en el sistema.
    Sirve como punto de acceso a diferentes visualizaciones de datos.
    """
    template_name = 'charts.html'

    def get_context_data(self, **kwargs):
        """
        Genera el contexto para la vista, con información de los gráficos disponibles.
        """
        context = super().get_context_data(**kwargs)
        context.update({
            "charts": [
                {"name": "Gráfico de Monitoreo", "url": "chart"},
                {"name": "Gráfico Dual", "url": "dual-chart"},
                {"name": "Gauges", "url": "gauges"},
                {"name": "Tabla de Coeficientes", "url": "table-coef"},
            ]
        })
        return context


class OldDevicesChartView(TemplateView):
    template_name = 'old-devices.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=24)
        
        # Obtener datos del período
        data = SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('timestamp', 'sensor', 't', 'h') 
        
        # Generar gráfico dual
        chart_html = generate_dual_plotly_chart(
            list(data),
            start_date,
            end_date
        )
        
        context['chart'] = chart_html
        return context

class GaugePartialView(TemplateView):
    template_name = 'partials/charts/gauges/gauge.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metric = kwargs['metric']
        sensor = kwargs['sensor']
        # Obtain the latest data for this sensor+metric here:
        latest = SensorData.objects.filter(sensor=sensor).order_by('-timestamp').first()
        gauge_value = latest.__dict__.get(metric, 0) if latest else 0
        context.update({
            'sensor': sensor,
            'metric': metric,
            'gauge_value': gauge_value
        })
        return context