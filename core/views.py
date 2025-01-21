# Python built-in
from datetime import datetime, timedelta, timezone
import requests

# Django y DRF
from django.views.generic import TemplateView
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings

# Local
from .models import SensorData
from .utils import old_devices_plot_generator, get_start_date, overview_plot_generator, sensor_plot_generator

@method_decorator(cache_page(60), name='dispatch')  # Cache for 1 minute
class HomeView(TemplateView):
    """Vista principal de la aplicación"""
    template_name = 'home.html'

@method_decorator(cache_page(60), name='dispatch')
class DevelopmentView(TemplateView):
    """Vista de desarrollo para pruebas"""
    template_name = 'development.html'

@method_decorator(cache_page(60), name='dispatch')
class ChartsView(TemplateView):
    template_name = "charts.html"

@method_decorator(cache_page(30), name='dispatch')  # Cache for 30 seconds
class OverviewView(TemplateView):
    template_name = "partials/charts/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de la solicitud
        timeframe = self.request.GET.get('timeframe', '1h')
        metric = self.request.GET.get('metric', 't')
        
        # Calcular fechas antes de la petición API
        end_date = datetime.now(timezone.utc)
        start_date = get_start_date(timeframe, end_date)

        # Construir URL usando INTERNAL_API_URL
        api_url = f"{settings.INTERNAL_API_URL}{reverse('sensor-data-timeframed')}"
        params = {
            'timeframe': timeframe,
            'metric': metric,
            'start_date': start_date.isoformat()
        }
        
        # Realizar petición a la API
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # Actualizar contexto
        context.update({
            'metadata': data.get('metadata', {}),
            'results': data.get('results', [])
        })
        
        chart_html, plotted_points = overview_plot_generator(
            context['results'],
            metric,
            start_date,
            end_date,
            timeframe,
            div_id='chart'
        )
        context.update({
            'chart_html': chart_html,
            'plotted_points': plotted_points
        })
        
        return context

@method_decorator(cache_page(60), name='dispatch')
class SensorsView(TemplateView):
    template_name = "partials/charts/sensors.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        timeframe = '4H'
        end_date = datetime.now(timezone.utc)
        start_date = get_start_date(timeframe, end_date)
        
        api_url = f"{settings.INTERNAL_API_URL}{reverse('sensor-data-timeframed')}"
        params = {
            'timeframe': timeframe,
            'start_date': start_date.isoformat()
        }
        response = requests.get(api_url, params=params)
        data = response.json()

        context.update({
            'metadata': data.get('metadata', {}),
            'results': data.get('results', [])
        })

        sensor_ids = context['metadata'].get('sensor_ids', [])
        charts = {}
        for sensor in sensor_ids:
            chart_html, _ = sensor_plot_generator(
                context['results'], 
                sensor, 
                start_date, 
                end_date, 
                timeframe, 
                div_id=f"chart_{sensor}"
            )
            charts[sensor] = chart_html

        context['charts'] = charts
        return context

@method_decorator(cache_page(60), name='dispatch')
class VPDView(TemplateView):
    template_name = "partials/charts/vpd.html"

@method_decorator(cache_page(30), name='dispatch')
class GaugesView(TemplateView):
    template_name = "partials/charts/gauges.html"

@method_decorator(cache_page(300), name='dispatch')  # Cache for 5 minutes
class OldDevicesChartView(TemplateView):
    template_name = 'old-devices.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=24)
        
        # Obtener datos del período
        data = SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('timestamp', 'sensor', 't', 'h') 
        
        # Generar gráfico dual
        chart_html = old_devices_plot_generator(
            list(data),
            start_date,
            end_date
        )
        
        context['chart'] = chart_html
        return context
        return context