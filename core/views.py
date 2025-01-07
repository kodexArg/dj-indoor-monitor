# Python built-in
from datetime import datetime, timedelta, timezone
import requests

# Django y DRF
from django.views.generic import TemplateView
from django.urls import reverse

# Local
from .models import SensorData
from .utils import old_devices_plot_generator, get_start_date, overview_plot_generator

class HomeView(TemplateView):
    """Vista principal de la aplicación"""
    template_name = 'home.html'

class DevelopmentView(TemplateView):
    """Vista de desarrollo para pruebas"""
    template_name = 'development.html'

class ChartsView(TemplateView):
    template_name = "charts.html"

class OverviewView(TemplateView):
    template_name = "partials/charts/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de la solicitud
        timeframe = self.request.GET.get('timeframe', '5s')
        metric = self.request.GET.get('metric', 't')
        
        # Calcular fechas antes de la petición API
        end_date = datetime.now(timezone.utc)
        start_date = get_start_date(timeframe, end_date)

        # Construir URL usando reverse y request actual
        api_url = self.request.build_absolute_uri(reverse('sensor-data-list'))
        params = {
            'timeframe': timeframe,
            'metric': metric,
            'start_date': start_date.isoformat()  # Añadir start_date a los parámetros
        }
        
        # Realizar petición a la API
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # Actualizar contexto con la nueva estructura
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

class SensorsView(TemplateView):
    template_name = "partials/charts/sensors.html"

class VPDView(TemplateView):
    template_name = "partials/charts/vpd.html"

class GaugesView(TemplateView):
    template_name = "partials/charts/gauges.html"

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