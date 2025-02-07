from datetime import datetime, timedelta, timezone
import requests
import numpy as np

from django.views.generic import TemplateView
from django.views import View
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse
from django.core.cache import cache

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
    template_name = 'home.html'

class DevelopmentView(TemplateView):
    template_name = 'development.html'

class ChartsView(TemplateView):
    template_name = "charts.html"

class OverviewView(TemplateView):
    template_name = "partials/charts/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        timeframe = self.request.GET.get('timeframe', '1h')
        metric = self.request.GET.get('metric', 't')
        room = self.request.GET.get('room', 'true')
        end_date = datetime.now(timezone.utc)
        start_date = get_start_date(timeframe, end_date)
        api_url = f"{settings.INTERNAL_API_URL}{reverse('sensor-data-timeframed')}"
        params = {
            'timeframe': timeframe,
            'metric': metric,
            'start_date': start_date.isoformat(),
            'room': room
        }
        data = requests.get(api_url, params=params).json()
        filtered_results = [
            {
                'timestamp': r.get('timestamp'),
                'sensor': r.get('sensor'),
                't': r.get('t'),
                'h': r.get('h')
            }
            for r in data.get('results', [])
        ]
        context.update({
            'room': room.lower() == 'true',
            'metadata': data.get('metadata', {}),
            'results': filtered_results
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
            'selected_timeframe': timeframe 
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
        params = {'room': 'false'}
        response_sensors = requests.get(api_url, params=params)
        sensor_data = response_sensors.json()
        temps = []
        hums = []
        valid_sensors = [] 
        for sensor in sensor_data:
            t = sensor.get('t')
            h = sensor.get('h')
            if (t is not None and h is not None and t >= 1 and h >= 1): 
                temps.append(t)
                hums.append(h)
                valid_sensors.append(sensor)
        sensor_to_room = {}
        for room in Room.objects.all():
            room_name = room.name
            for sensor in room.sensors.split(','):
                sensor = sensor.strip()
                if sensor:
                    sensor_data = next((s for s in valid_sensors if s['sensor'] == sensor), None)
                    if sensor_data and sensor_data.get('t') is not None and sensor_data.get('h') is not None:
                        sensor_to_room[sensor] = room_name 
        temps = np.array(temps)
        hums = np.array(hums)
        es = 0.6108 * np.exp((17.27 * temps) / (temps + 237.3))
        vpds = es * (1 - (hums / 100))
        sensors_info = []
        for idx, sensor in enumerate(valid_sensors):  
            sensors_info.append({
                'room': sensor_to_room.get(sensor['sensor'], "Sin Asignar"),
                'sensor': sensor['sensor'],
                't': temps[idx],
                'h': hums[idx],
                'vpd': vpds[idx]
            })
        sensors_info = sorted(sensors_info, key=lambda x: (x['room'], x['sensor']))
        room_averages = {}
        for sensor_info in sensors_info:
            room = sensor_info['room']
            if room not in room_averages:
                room_averages[room] = {'t': [], 'h': []}
            room_averages[room]['t'].append(sensor_info['t'])
            room_averages[room]['h'].append(sensor_info['h'])
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
    template_name = 'partials/charts/gauges.html'
    
    METRIC_TITLES = {
        't': 'Temperatura',
        'h': 'Humedad',
        's': 'Suelo',
        'l': 'Luz',
        'r': 'Lluvia'
    }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        api_url = f"{settings.INTERNAL_API_URL}/sensor-data/latest/"
        response = requests.get(api_url, timeout=5)
        data_points = response.json()

        metrics_data = {}
        for point in data_points:
            for metric in ['t', 'h']:
                value = point.get(metric)
                if value is not None:
                    if metric not in metrics_data:
                        metrics_data[metric] = []
                    metrics_data[metric].append({
                        'value': value,
                        'metric': metric,
                        'sensor': point['sensor']
                    })

        gauges_by_metric = []
        for metric, gauges in metrics_data.items():
            if gauges:
                gauges_by_metric.append({
                    'title': self.METRIC_TITLES.get(metric, metric.upper()),
                    'gauges': gauges
                })

        gauges_by_metric.sort(key=lambda x: x['title'])
        context['gauges_by_metric'] = gauges_by_metric
        return context

class GenerateGaugeView(View):
    def get(self, request, *args, **kwargs):
        sensor = request.GET.get('sensor', '')
        metric = request.GET.get('metric', '')
        cache_key = f'last_value_{sensor}_{metric}'

        try:
            value_str = request.GET.get('value', '').replace(',', '.')
            value = float(value_str)
            
            if value == 0:
                value = cache.get(cache_key)
                if value is None:
                    return HttpResponse('')
            else:
                cache.set(cache_key, value, timeout=60 * 10) 

        except ValueError:
            value = cache.get(cache_key)
            if value is None:
                return HttpResponse('')

        if value is not None:
            gauge = gauge_generator(
                value=value,
                metric=metric,
                sensor=sensor
            )
            return HttpResponse(gauge)
        else:
            return HttpResponse('') 

class OldDevicesChartView(TemplateView):
    template_name = 'old-devices.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=24)
        data = SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('timestamp', 'sensor', 't', 'h') 
        chart_html = old_devices_plot_generator(
            list(data),
            start_date,
            end_date
        )
        context['chart'] = chart_html
        return context