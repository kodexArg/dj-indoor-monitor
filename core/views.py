from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from collections import OrderedDict
from .models import DataPoint, Sensor
from .charts import gauge_plot, sensor_plot, calculate_vpd, vpd_plot
from .utils import get_timedelta_from_timeframe, create_timeframed_dataframe # funciones
from .utils import METRIC_MAP # constantes
from .utils import DataPointDataFrameBuilder # clases
import pandas as pd

class HomeView(TemplateView):
    template_name = 'development.html'

class DevelopmentView(TemplateView):
    template_name = 'development.html'

class ChartsView(TemplateView):
    template_name = 'charts.html'

class OverviewView(TemplateView):
    template_name = 'charts/overview.html'


class GaugesView(TemplateView):
    template_name = 'charts/gauges.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate the date 24 hours ago
        cutoff_date = timezone.now() - timezone.timedelta(hours=24)

        # Get the latest data points for each sensor and metric
        latest_data_points = DataPoint.objects.filter(timestamp__gte=cutoff_date).order_by(
            'sensor', 'metric', '-timestamp'
        ).distinct('sensor', 'metric')

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
                    'timestamp': data_point.timestamp.isoformat() if data_point.timestamp else None,
                })

        for room_name, gauges in gauges_by_room.items():
            gauges.sort(key=lambda x: (x['metric'], x['sensor_name']))

        context['gauges_by_room'] = gauges_by_room
        return context


class SensorsView(TemplateView):
    template_name = 'charts/sensors.html'
    metric_map = METRIC_MAP

    def get_context_data(self, **kwargs):
        """
        Prealiza una consulta al modelo Sensor para obtener cada sensor,
        agrupado por habitación y cada métrica disponible.
        
        Template recibe un diccionario anidado 'data' con el siguiente formato:
        {
            'RoomName': {
                'metric_code': {
                    'metric': <letra>,
                    'metric_name': <nombre completo>,
                    'sensors': [sensor1, sensor2, ...]
                },
                ...
            },
            ...
        }
        """
        context = super().get_context_data(**kwargs)
        timeframe = self.request.GET.get('timeframe', '1h').lower()
        context['timeframe'] = timeframe
        context['selected_timeframe'] = timeframe # Pass the selected timeframe to the template

        data = {}
        sensors = Sensor.objects.select_related('room').all()
        from .models import DataPoint  # Ensure DataPoint is imported if needed.
        for sensor in sensors:
            if not sensor.room:
                continue
            room_name = sensor.room.name
            if room_name not in data:
                data[room_name] = {}

            # Query DataPoint filtering by sensor name.
            sensor_metrics = DataPoint.objects.filter(sensor=sensor.name).values_list('metric', flat=True).distinct()

            # Custom metric ordering
            metric_order = ['t', 'h', 'l', 's']
            ordered_metrics = OrderedDict()

            for metric_code in metric_order:
                if metric_code in sensor_metrics:
                    ordered_metrics[metric_code] = None

            for metric_code in sorted(sensor_metrics):
                if metric_code not in ordered_metrics:
                    ordered_metrics[metric_code] = None

            for metric_code in ordered_metrics:
                metric_name = self.metric_map.get(metric_code, metric_code)
                if metric_code not in data[room_name]:
                    data[room_name][metric_code] = {
                        'metric': metric_code,
                        'metric_name': metric_name,
                        'sensors': []
                    }
                if sensor.name not in data[room_name][metric_code]['sensors']:
                    data[room_name][metric_code]['sensors'].append(sensor.name)

        # Reorder metrics based on metric_order
        for room_name, room_data in data.items():
            ordered_data = OrderedDict()
            for metric_code in metric_order:
                if metric_code in room_data:
                    ordered_data[metric_code] = room_data[metric_code]
            for metric_code in room_data:
                if metric_code not in ordered_data:
                    ordered_data[metric_code] = room_data[metric_code]
            data[room_name] = ordered_data

        context['data'] = data

        return context

@method_decorator(csrf_exempt, name='dispatch') # Es método POST, se deshabilita CSRF
class GenerateSensorView(View):
    def post(self, request):
        sensor = request.POST.get('sensor')
        timeframe = request.POST.get('timeframe', '1h').lower()
        metric = request.POST.get('metric', '')
        
        end_date = timezone.now()
        start_date = timezone.now() - get_timedelta_from_timeframe(timeframe)
        
        data_points = DataPoint.objects.filter(
            sensor=sensor,
            metric=metric,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
        if not data_points:
            return HttpResponse("No data available for this sensor.")
        
        df = create_timeframed_dataframe(data_points, timeframe, start_date, end_date)

        chart_html, count = sensor_plot(df, sensor, metric, timeframe, start_date, end_date)
        
        return HttpResponse(chart_html)


class VPDView(TemplateView):
    template_name = 'charts/vpd.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        five_minutes_ago = now - timezone.timedelta(minutes=5)

        table_builder = DataPointDataFrameBuilder(
            timeframe='5Min',
            start_date=five_minutes_ago,
            end_date=now,
            metrics=['t', 'h'],
            pivot_metrics=True,
            use_last=True
        )

        # import pdb; pdb.set_trace()
        df_table = table_builder.build()

        if df_table.empty:
            context['room_data'] = []
            context['chart'] = vpd_plot([])
            return context

        df_table['timestamp'] = pd.to_datetime(df_table['timestamp'])
        sensores = Sensor.objects.all()
        sensor_room_map = {
            sensor.name: sensor.room.name if sensor.room else "No Room"
            for sensor in sensores
        }

        df_table['room'] = df_table['sensor'].apply(lambda s: sensor_room_map.get(s, "No Instalado"))

        room_data = df_table.to_dict(orient='records')

        chart_data = {}
        for item in room_data:
            temp = item.get('t')
            hum = item.get('h')
            room = item.get('room')
            if temp is None or hum is None:
                continue
            chart_data.setdefault(room, {'t': [], 'h': []})
            chart_data[room]['t'].append(temp)
            chart_data[room]['h'].append(hum)

        chart_data_list = []
        for room, values in chart_data.items():
            if values['t'] and values['h']:
                avg_temp = sum(values['t']) / len(values['t'])
                avg_hum = sum(values['h']) / len(values['h'])
                chart_data_list.append((room, avg_temp, avg_hum))

        context['room_data'] = room_data
        context['chart'] = vpd_plot(chart_data_list)

        return context


class GenerateGaugeView(View):
    def get(self, request, *args, **kwargs):
        sensor_name = request.GET.get('sensor', '')
        metric = request.GET.get('metric', '')
        timestamp_str = request.GET.get('timestamp')

        try:
            value_str = request.GET.get('value', '').replace(',', '.')
            value = float(value_str)
        except ValueError:
            return HttpResponse('')

        # Convert timestamp string to datetime object
        timestamp = timezone.datetime.fromisoformat(timestamp_str) if timestamp_str else None

        gauge_html = gauge_plot(
            value=value,
            metric=metric,
            sensor=sensor_name,
            timestamp=timestamp
        )
        return HttpResponse(gauge_html)
