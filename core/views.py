# Python built-in
from datetime import datetime, timedelta, timezone
import requests

# Django y DRF
from django.views.generic import TemplateView
from django.urls import reverse
from django.conf import settings

# Local
from .models import SensorData, Room
from .utils import old_devices_plot_generator, get_start_date, overview_plot_generator, sensor_plot_generator, vpd_chart_generator


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
        timeframe = self.request.GET.get('timeframe', '1h')
        metric = self.request.GET.get('metric', 't')
        room = self.request.GET.get('room', 'true')
        
        # Calcular fechas antes de la petición API
        end_date = datetime.now(timezone.utc)
        start_date = get_start_date(timeframe, end_date)

        # Construir URL usando INTERNAL_API_URL
        api_url = f"{settings.INTERNAL_API_URL}{reverse('sensor-data-timeframed')}"
        params = {
            'timeframe': timeframe,
            'metric': metric,
            'start_date': start_date.isoformat(),
            'room': room
        }
        
        # Realizar petición a la API
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # Actualizar contexto
        context.update({
            'room': room.lower() == 'true',  # Agregar room al contexto como boolean
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        timeframe = self.request.GET.get('timeframe', '4H')
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
            'results': data.get('results', []),
            'selected_timeframe': timeframe  # Add selected timeframe to context
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



class VPDView(TemplateView):
    template_name = "partials/charts/vpd.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        api_url = f"{settings.INTERNAL_API_URL}{reverse('sensor-data-latest')}"
        
        # Usar room=true según la API
        params = {'room': 'true'}
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # Procesar datos usando el sensor como nombre de room
        sensors_data = []
        for item in data:
            if item.get('t') is not None and item.get('h') is not None:
                sensors_data.append((item['sensor'], item['t'], item['h']))
        
        chart_html = vpd_chart_generator(sensors_data)
        context['chart'] = chart_html
        
        return context


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