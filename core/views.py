from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from .models import DataPoint, Sensor, Room
from .charts import gauge_generator  # Correct import

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

        # Agrupar por sala (room)
        gauges_by_room = {}
        for data_point in latest_data_points:
            sensor = sensors_dict.get(data_point.sensor)
            if sensor:
                room_name = sensor.room.name if sensor.room else "No Room"  # Default if no room
                if room_name not in gauges_by_room:
                    gauges_by_room[room_name] = []

                gauges_by_room[room_name].append({
                    'value': data_point.value,
                    'metric': data_point.metric,
                    'sensor_name': data_point.sensor,
                })

        # Ordenar cada lista de gauges dentro de cada sala
        for room_name, gauges in gauges_by_room.items():
            gauges.sort(key=lambda x: (x['metric'], x['sensor_name']))

        # Ensure "I+D" room is last
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