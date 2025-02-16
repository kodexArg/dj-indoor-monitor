from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import timezone
import pandas as pd
from collections import defaultdict

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import DataPoint, Sensor
from .charts import gauge_generator, lineplot_generator
from .utils import  get_start_date
import logging

logger = logging.getLogger(__name__)

class HomeView(TemplateView):
    template_name = 'development.html'

class DevelopmentView(TemplateView):
    template_name = 'development.html'

class ChartsView(TemplateView):
    template_name = 'charts.html'

class OverviewView(TemplateView):
    template_name = 'charts/overview.html'

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


class SensorsView(TemplateView):
    template_name = 'charts/sensors.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sensors = Sensor.objects.select_related('room').all()
        sensors_by_room = defaultdict(list)
        for sensor in sensors:
            if not sensor.room:
                continue
            room_name = sensor.room.name
            sensors_by_room[room_name].append({
                'sensor_name': sensor.name,
                'room_name': room_name,
            })

        for room, sensor_list in sensors_by_room.items():
            sensor_list.sort(key=lambda x: x['sensor_name'])

        context['sensors_by_room'] = sensors_by_room
        context['timeframe'] = self.request.GET.get('timeframe', '1h')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class GenerateSensorView(View):
    def get(self, request, *args, **kwargs):
        sensor_name = request.GET.get('sensor', '')
        timeframe = request.GET.get('timeframe', '1h')
        
        try:
            sensor = Sensor.objects.get(name=sensor_name)
            end_date = timezone.now()
            start_date = get_start_date(timeframe, end_date)

            data_points = DataPoint.objects.filter(
                sensor=sensor_name,
                timestamp__gte=start_date,
                timestamp__lte=end_date
            ).order_by('timestamp')

            if not data_points:
                return HttpResponse("No data available for this sensor.")

            df = pd.DataFrame(list(data_points.values()))
            if df.empty:
                return HttpResponse("No data available for this sensor.")
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            full_index = pd.date_range(
                start=df.index.min().floor('min'),
                end=df.index.max().ceil('min'),
                freq=timeframe
            )
            df = df.reindex(full_index)

            df.interpolate(method='linear', limit_direction='both', inplace=True)
            df = df.ffill().bfill()
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'timestamp'}, inplace=True)
            df['timestamp'] = df['timestamp'].dt.floor('min')

            metric = data_points.first().metric
            chart_html, count = lineplot_generator(df, sensor_name, metric)
            return HttpResponse(chart_html)
        
        except Exception as e:
            logger.error(f"Error en GenerateSensorView: {str(e)}")
            return HttpResponse(f'Error generating the chart: {str(e)}')