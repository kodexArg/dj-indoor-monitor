# Python built-in
from datetime import datetime, timedelta, timezone
import requests
import numpy as np

# Django y DRF
from django.views.generic import TemplateView
from django.views import View
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse

# Local
from .models import SensorData, Room
from .utils import (
    old_devices_plot_generator,
    get_start_date,
    overview_plot_generator,
    sensor_plot_generator,
    vpd_chart_generator,
    gauge_generator
)


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
        
        # Solo necesitamos una llamada para obtener datos individuales de sensores
        params = {'room': 'false'}
        response_sensors = requests.get(api_url, params=params)
        sensor_data = response_sensors.json()

        # Procesar datos de sensores individuales
        temps = []
        hums = []
        valid_sensors = []  # Lista para mantener los sensores válidos
        
        for sensor in sensor_data:
            t = sensor.get('t')
            h = sensor.get('h')
            if (t is not None and h is not None and    t >= 1 and h >= 1): 
                temps.append(t)
                hums.append(h)
                valid_sensors.append(sensor)
    
        # Obtener mapeo de sensores a rooms desde el modelo Room
        sensor_to_room = {}
        for room in Room.objects.all():
            room_name = room.name
            for sensor in room.sensors.split(','):
                sensor = sensor.strip()  # Corregida la indentación
                if sensor:
                    sensor_data = next((s for s in valid_sensors if s['sensor'] == sensor), None)
                    if sensor_data and sensor_data.get('t') is not None and sensor_data.get('h') is not None:
                        sensor_to_room[sensor] = room_name  # Corregida la indentación
                
        # Cálculo vectorizado de VPD usando numpy
        temps = np.array(temps)
        hums = np.array(hums)
        es = 0.6108 * np.exp((17.27 * temps) / (temps + 237.3))
        vpds = es * (1 - (hums / 100))
        
        # Construir estructura final de datos
        sensors_info = []
        for idx, sensor in enumerate(valid_sensors):  # Usar valid_sensors en lugar de sensor_data
            sensors_info.append({
                'room': sensor_to_room.get(sensor['sensor'], "Sin Asignar"),
                'sensor': sensor['sensor'],
                't': temps[idx],
                'h': hums[idx],
                'vpd': vpds[idx]
            })

        # Ordenar por room y luego por sensor
        sensors_info = sorted(sensors_info, key=lambda x: (x['room'], x['sensor']))
        
        # Calcular promedios por room para el gráfico
        room_averages = {}
        for sensor_info in sensors_info:
            room = sensor_info['room']
            if room not in room_averages:
                room_averages[room] = {'t': [], 'h': []}
            room_averages[room]['t'].append(sensor_info['t'])
            room_averages[room]['h'].append(sensor_info['h'])

        # Preparar datos para el gráfico usando promedios por room
        chart_data = []
        for room, values in room_averages.items():
            avg_temp = sum(values['t']) / len(values['t'])
            avg_hum = sum(values['h']) / len(values['h'])
            chart_data.append((room, avg_temp, avg_hum))
        
        context.update({
            'room_data': sensors_info,
            'chart': vpd_chart_generator(chart_data)
        })
        return context


class GaugesView(TemplateView):
    """Vista principal de gauges que obtiene datos iniciales"""
    template_name = "partials/charts/gauges.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        api_url = f"{settings.INTERNAL_API_URL}{reverse('sensor-data-latest')}"
        response = requests.get(api_url, params={'room': 'true'})
        rooms_data = response.json()

        gauges_data = []
        for room in rooms_data:
            gauges_data.append({
                'room': room['sensor'],
                'sensor': room.get('sensor_id', ''),  # sensor_id debe venir de la API
                'value': room['t'],
                'metric': 't'
            })
            gauges_data.append({
                'room': room['sensor'],
                'sensor': room.get('sensor_id', ''),
                'value': room['h'],
                'metric': 'h'
            })

        context['gauges'] = gauges_data
        return context

class GenerateGaugeView(View):
    """Vista que genera y retorna el HTML de un gauge individual"""
    def get(self, request, *args, **kwargs):
        try:
            value_str = request.GET.get('value', '0').replace(',', '.')
            value = float(value_str)
        except ValueError:
            value = 0.0
            
        room = request.GET.get('room', '')
        sensor = request.GET.get('sensor', '')
        metric = request.GET.get('metric', '')
        
        gauge = gauge_generator(
            value=value,
            metric=metric,
            room=room,
            sensor=sensor
        )
        
        return HttpResponse(gauge)

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