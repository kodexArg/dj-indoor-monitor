from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import DataPoint, Sensor
from .charts import gauge_generator, sensor_plot
from .utils import get_timedelta_from_timeframe, create_timeframed_dataframe, METRIC_MAP
from collections import OrderedDict

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

        print(100 * '-')
        print(context)
        print(100 * '-')
        return context

@method_decorator(csrf_exempt, name='dispatch')
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