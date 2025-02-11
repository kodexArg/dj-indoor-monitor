from django.views.generic import TemplateView
from django.views import View
from django.http import HttpResponse
from django.conf import settings
import requests

# Local
from .models import DataPoint
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
        api_url = f"{settings.INTERNAL_API_URL}/data-point/latest/"
        response = requests.get(api_url, timeout=5)
        data_points = response.json()
        
        serialized_data = DataPointSerializer(data_points, many=True).data

        metrics_data = {}
        for point in serialized_data:
            if point['metric'] in ['t', 'h']:
                metric = point['metric']
                if metric not in metrics_data:
                    metrics_data[metric] = []
                metrics_data[metric].append({
                    'value': point['value'],
                    'metric': metric,
                    'sensor': point['sensor'],
                    'room': point['room']
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
