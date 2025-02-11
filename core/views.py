from django.views.generic import TemplateView
from django.views import View
from django.http import HttpResponse
from django.conf import settings
import requests
from django.db.models import Max

# Local
from .models import DataPoint, Sensor  # Import Sensor
from .charts import gauge_generator
from .serializers import DataPointSerializer


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
    
    METRIC_TITLES = {
        't': 'Temperatura',
        'h': 'Humedad',
    }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch the latest DataPoint for each sensor and metric
        latest_data_points = DataPoint.objects.values('sensor', 'metric').annotate(
            last_timestamp=Max('timestamp')
        ).values('sensor', 'metric', 'last_timestamp')

        metrics_data = {}
        for item in latest_data_points:
            data_point = DataPoint.objects.get(
                sensor=item['sensor'],
                metric=item['metric'],
                timestamp=item['last_timestamp']
            )

            sensor = Sensor.objects.get(name=data_point.sensor)

            if data_point.metric in ['t', 'h']:
                metric = data_point.metric
                if metric not in metrics_data:
                    metrics_data[metric] = []
                metrics_data[metric].append({
                    'value': data_point.value,
                    'metric': data_point.metric,
                    'sensor': data_point.sensor,
                    'room': sensor.room.name if sensor.room else None 
                })

        gauges_by_metric = []
        for metric, gauges in metrics_data.items():
            if gauges:
                gauges_by_metric.append({
                    'title': self.METRIC_TITLES.get(metric, metric.upper()),
                    'gauges': gauges
                })

        context['gauges_by_metric'] = gauges_by_metric
        return context

class GenerateGaugeView(View):
    def get(self, request, *args, **kwargs):
        sensor = request.GET.get('sensor', '')
        metric = request.GET.get('metric', '')

        try:
            value_str = request.GET.get('value', '').replace(',', '.')
            value = float(value_str)

        except ValueError:
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
