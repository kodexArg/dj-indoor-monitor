from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import pandas as pd
from collections import defaultdict
import json

from .models import DataPoint, Sensor, Room
from .charts import gauge_generator, lineplot_generator
from .utils import get_timedelta_from_timeframe, get_start_date

class HomeView(TemplateView):
    template_name = 'development.html'

class DevelopmentView(TemplateView):
    template_name = 'development.html'

class ChartsView(TemplateView):
    template_name = 'charts.html'

class OverviewView(TemplateView):
    template_name = 'charts/overview.html'

class SensorsView(TemplateView):
    template_name = 'charts/sensors.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        timeframe = request.GET.get('timeframe', '1H')
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')
        if end_date_param:
            end_date = parse_datetime(end_date_param)
        else:
            end_date = timezone.now()
        if start_date_param:
            start_date = parse_datetime(start_date_param)
        else:
            start_date = get_start_date(timeframe, end_date)

        data_points = DataPoint.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date).order_by('timestamp')

        sensors_dict = {sensor.name: sensor for sensor in Sensor.objects.select_related('room').all()}

        temp = defaultdict(list)
        for dp in data_points:
            temp[(dp.sensor, dp.metric)].append((dp.timestamp, dp.value))

        sensors_by_room = {}
        for (sensor_name, metric), raw_values in temp.items():
            df = pd.DataFrame(raw_values, columns=['timestamp', 'value'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df_grouped = df.resample(timeframe).mean().dropna().reset_index()
            grouped_values = list(zip(df_grouped['timestamp'], df_grouped['value']))
            
            sensor_obj = sensors_dict.get(sensor_name)
            if not sensor_obj or not sensor_obj.room:
                continue
            room_name = sensor_obj.room.name
            sensors_by_room.setdefault(room_name, []).append({
                'sensor_name': sensor_name,
                'metric': metric,
                'values': grouped_values
            })

        for room, sensor_list in sensors_by_room.items():
            sensor_list.sort(key=lambda x: (x['metric'], x['sensor_name']))

        context['sensors_by_room'] = sensors_by_room
        context['selected_timeframe'] = timeframe
        return context

class VPDView(TemplateView):
    template_name = 'charts/vpd.html'

class GaugesView(TemplateView):
    template_name = 'charts/gauges.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        latest_data_points = DataPoint.objects.annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F('sensor'), F('metric')],
                order_by=F('timestamp').desc(),
            )
        ).filter(row_number=1)

        sensors_dict = {sensor.name: sensor for sensor in Sensor.objects.select_related('room').all()}

        gauges_by_room = {}
        for data_point in latest_data_points:
            sensor = sensors_dict.get(data_point.sensor)
            if sensor:
                room_name = sensor.room.name if sensor.room else "No Room"
                if room_name not in gauges_by_room:
                    gauges_by_room[room_name] = []

                gauges_by_room[room_name].append({
                    'value': data_point.value,
                    'metric': data_point.metric,
                    'sensor_name': data_point.sensor,
                })

        for room_name, gauges in gauges_by_room.items():
            gauges.sort(key=lambda x: (x['metric'], x['sensor_name']))

        if "I+D" in gauges_by_room:
            gauges_by_room["I+D"] = gauges_by_room.pop("I+D")

        context['gauges_by_room'] = gauges_by_room
        return context

class GenerateSensorView(View):
    def get(self, request, *args, **kwargs):
        sensor_name = request.GET.get('sensor', '')
        metric = request.GET.get('metric', '')
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')
        start_date = parse_datetime(start_date_param)
        end_date = parse_datetime(end_date_param)

        values_json = request.GET.get('values', '[]')
        try:
            values = json.loads(values_json)
        except Exception:
            values = []

        chart_html, _ = lineplot_generator(values, sensor_name, metric, start_date, end_date)
        return HttpResponse(chart_html)

class GenerateGaugeView(View):
    def get(self, request, *args, **kwargs):
        sensor_name = request.GET.get('sensor', '')
        metric = request.GET.get('metric', '')

        try:
            value_str = request.GET.get('value', '').replace(',', '.')
            value = float(value_str)
        except ValueError:
            return HttpResponse('')

        gauge_html = gauge_generator(
            value=value,
            metric=metric,
            sensor=sensor_name
        )
        return HttpResponse(gauge_html)