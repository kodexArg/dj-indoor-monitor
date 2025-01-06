# Python built-in
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from time import perf_counter

# Django y DRF
from django.conf import settings
from django.db.models import QuerySet, Min, Max, Count
from django.db.models.functions import TruncSecond, TruncMinute, TruncHour, TruncDay
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from loguru import logger
import pandas as pd

# Local
from .models import SensorData
from .serializers import SensorDataSerializer
from .filters import SensorDataFilter
from .utils import old_devices_plot_generator


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

class SensorsView(TemplateView):
    template_name = "partials/charts/sensors.html"

class VPDView(TemplateView):
    template_name = "partials/charts/vpd.html"

class GaugesView(TemplateView):
    template_name = "partials/charts/gauges.html"

class OldDevicesChartView(TemplateView):
    template_name = 'old-devices.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
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