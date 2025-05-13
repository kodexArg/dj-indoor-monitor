from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from collections import OrderedDict
from .models import DataPoint, Sensor
from .charts import gauge_plot, sensor_plot, vpd_plot, calculate_vpd
from .utils import get_timedelta_from_timeframe, create_timeframed_dataframe
from .utils import METRIC_MAP
from .utils import DataPointDataFrameBuilder
from .utils import pretty_datetime, get_start_date
import pandas as pd
import time
from loguru import logger

class HomeView(TemplateView):
    template_name = 'home.html'

class DevelopmentView(TemplateView):
    template_name = 'development.html'

class ChartsView(TemplateView):
    template_name = 'charts.html'


class GaugesView(TemplateView):
    template_name = 'charts/gauges.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cutoff_date = timezone.now() - timezone.timedelta(hours=24)

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
        start_time = time.time()
        
        context = super().get_context_data(**kwargs)
        timeframe = self.request.GET.get('timeframe', '1h').lower()
        context['timeframe'] = timeframe
        context['selected_timeframe'] = timeframe
        
        # Calcular el rango de tiempo para filtrar datos
        end_date = timezone.now()
        start_date = end_date - get_timedelta_from_timeframe(timeframe)

        data = {}
        sensors = Sensor.objects.select_related('room').all()
        
        # Optimización: obtener todas las métricas de todos los sensores en una sola consulta
        # y crear un diccionario para acceso rápido, pero filtrando por el rango de tiempo
        all_sensor_metrics = {}
        sensor_names = [sensor.name for sensor in sensors if sensor.room]
        
        if sensor_names:
            # Consulta modificada para filtrar por rango de tiempo
            metrics_by_sensor = DataPoint.objects.filter(
                sensor__in=sensor_names,
                timestamp__gte=start_date,
                timestamp__lte=end_date
            ).values('sensor', 'metric').distinct()
            
            for item in metrics_by_sensor:
                sensor_name = item['sensor']
                metric = item['metric']
                if sensor_name not in all_sensor_metrics:
                    all_sensor_metrics[sensor_name] = set()
                all_sensor_metrics[sensor_name].add(metric)
        
        metric_order = ['t', 'h', 'l', 's']
        
        for sensor in sensors:
            if not sensor.room:
                continue
                
            room_name = sensor.room.name
            if room_name not in data:
                data[room_name] = {}

            sensor_metrics = all_sensor_metrics.get(sensor.name, set())
            
            if not sensor_metrics:
                logger.debug(f"Sensor '{sensor.name}' en sala '{room_name}' no tiene datos en el rango de tiempo {timeframe}")
                continue

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
        
        total_time = time.time() - start_time
        logger.debug(f"SensorsView: Renderizado en {total_time:.2f}s con {len(all_sensor_metrics)} sensores activos")

        return context

@method_decorator(csrf_exempt, name='dispatch')
class GenerateSensorView(View):
    def post(self, request):
        start_time = time.time()
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
            logger.warning(f"No hay datos para sensor='{sensor}', metric='{metric}' en rango {timeframe}")
            return HttpResponse(f"<div class='no-data-alert'>No hay datos disponibles para el sensor {sensor}</div>")
        
        df = create_timeframed_dataframe(data_points, timeframe, start_date, end_date)
        chart_html, count = sensor_plot(df, sensor, metric, timeframe, start_date, end_date)
        
        total_time = time.time() - start_time
        logger.debug(f"Gráfico para {sensor}/{metric}: {count} puntos en {total_time:.2f}s")
        
        return HttpResponse(chart_html)


class VPDView(TemplateView):
    template_name = 'charts/vpd.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        minutes_ago = now - timezone.timedelta(minutes=15)

        table_builder = DataPointDataFrameBuilder(
            timeframe='5Min',
            start_date=minutes_ago,
            end_date=now,
            metrics=['t', 'h'],
            pivot_metrics=True,
            use_last=True
        )
        df_table = table_builder.build()

        if df_table.empty:
            context['room_data'] = []
            context['chart'] = vpd_plot([])
            return context

        df_table['timestamp'] = pd.to_datetime(df_table['timestamp'])
        sensores = Sensor.objects.all()
        sensor_room_map = {sensor.name: sensor.room.name if sensor.room else "No Room" for sensor in sensores}
        df_table['room'] = df_table['sensor'].apply(lambda s: sensor_room_map.get(s, "No Instalado"))
        
        df_table['vpd'] = df_table.apply(lambda row: calculate_vpd(row['t'], row['h']), axis=1)

        context['room_data'] = df_table.to_dict(orient='records')

        chart_builder = DataPointDataFrameBuilder(
            timeframe='5Min',
            start_date=minutes_ago,
            end_date=now,
            metrics=['t', 'h'],
            pivot_metrics=True,
            use_last=True
        )
        
        df_grouped_chart = chart_builder.group_by_room()

        data_for_chart = []
        for room, group in df_grouped_chart:
            if 't' in group.columns and 'h' in group.columns:
                avg_t = group['t'].mean()
                avg_h = group['h'].mean()
                data_for_chart.append((room, avg_t, avg_h))
        
        chart_html = vpd_plot(data_for_chart)

        context['chart'] = chart_html

            
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

        timestamp = timezone.datetime.fromisoformat(timestamp_str) if timestamp_str else None

        gauge_html = gauge_plot(
            value=value,
            metric=metric,
            sensor=sensor_name,
            timestamp=timestamp
        )
        return HttpResponse(gauge_html)


class InteractiveView(TemplateView):
    template_name = 'charts/interactive.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        timeframe = self.request.GET.get('timeframe', '4h').lower()
        metric = self.request.GET.get('metric', 't').lower()
        room = self.request.GET.get('room', 'true').lower() == 'true'

        end_date_str = self.request.GET.get('end_date')
        end_date = timezone.datetime.fromisoformat(end_date_str) if end_date_str else timezone.now()

        start_date_str = self.request.GET.get('start_date')
        if start_date_str:
            start_date = timezone.datetime.fromisoformat(start_date_str)
        else:
            start_date = get_start_date(timeframe, end_date)

        

        context['metadata'] = {
            'timeframe': timeframe,
            'metric': metric,
            'start': start_date,
            'end': end_date,
            'start_pretty': pretty_datetime(start_date),
            'end_pretty': pretty_datetime(end_date),
        }
        context['room'] = room

        return context
