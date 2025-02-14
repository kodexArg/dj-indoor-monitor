import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import pandas as pd
from collections import defaultdict
import json

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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

        # Modificar el timeframe default a 'h' en lugar de 'H'
        timeframe = request.GET.get('timeframe', '1h')
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
            df['value'] = df['value'].round(1)
            df.set_index('timestamp', inplace=True)
            # Crear un índice continuo usando el rango completo y reindexar
            full_index = pd.date_range(start=df.index.min().floor('min'),
                                       end=df.index.max().ceil('min'),
                                       freq=timeframe)
            df = df.reindex(full_index)
            # Rellenar puntos faltantes con interpolación lineal 
            df.interpolate(method='linear', limit_direction='both', inplace=True)
            # Si aún quedan NaN (por ejemplo, si no había ningún dato válido), aplicar ffill y bfill
            df = df.ffill().bfill()
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'timestamp'}, inplace=True)
            df['timestamp'] = df['timestamp'].dt.floor('min')
            
            # Convertir valores NaN a None para JSON
            values_list = df['value'].apply(lambda x: None if pd.isna(x) else x).tolist()
            timestamps_list = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()
            formatted_values = list(zip(timestamps_list, values_list))
            
            json_values = json.dumps(formatted_values)
            
            sensor_obj = sensors_dict.get(sensor_name)
            if not sensor_obj or not sensor_obj.room:
                continue
            room_name = sensor_obj.room.name
            sensors_by_room.setdefault(room_name, []).append({
                'sensor_name': sensor_name,
                'metric': metric,
                'values': json_values  # Now this is a properly formatted JSON string
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


@method_decorator(csrf_exempt, name='dispatch')
class GenerateSensorView(View):
    def post(self, request, *args, **kwargs):
        sensor_name = request.POST.get('sensor', '')
        metric = request.POST.get('metric', '')
        values_json = request.POST.get('values', '[]')
        
        try:
            values = json.loads(values_json)
            logger.info(f"Valores recibidos: {values[:5]}...")
            
            if not values:
                logger.warning("No se recibieron valores")
                return HttpResponse("No hay datos para mostrar")

            df = pd.DataFrame(values, columns=['timestamp', 'value'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            
            logger.info(f"DataFrame inicial:\n{df.head()}")
            logger.info(f"Tipos de datos: {df.dtypes}")
            
            df.set_index('timestamp', inplace=True)

            timeframe = '1h'
            full_index = pd.date_range(
                start=df.index.min().floor('min'),
                end=df.index.max().ceil('min'),
                freq=timeframe
            )
            df = df.reindex(full_index)
            
            logger.info(f"DataFrame antes de interpolar:\n{df.head()}")
            
            # Interpolar valores faltantes
            df.interpolate(method='linear', limit_direction='both', inplace=True)
            # Usar ffill() y bfill() en lugar de fillna(method=...)
            df = df.ffill().bfill()
            
            # Logging después de interpolar
            logger.info(f"DataFrame después de interpolar:\n{df.head()}")
            
            # Si después de interpolar no hay valores válidos, terminar
            if df['value'].isna().all():
                logger.warning("No hay datos válidos después de interpolar")
                return HttpResponse("No hay datos válidos para mostrar")

            # Preparar datos para el gráfico
            df.reset_index(inplace=True)
            timestamps = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()
            data_values = df['value'].round(1).tolist()
            
            valid_points_count = len([v for v in data_values if v is not None])
            logger.info(f"Puntos válidos después de interpolar: {valid_points_count}")
            
            if valid_points_count == 1:
                chart_html, count = scatter_generator(
                    timestamps,
                    data_values,
                    sensor_name,
                    metric
                )
            else:
                chart_html, count = lineplot_generator(
                    timestamps,
                    data_values,
                    sensor_name,
                    metric
                )
            
            logger.info(f"Gráfico generado con {count} puntos")
            return HttpResponse(chart_html)
            
        except Exception as e:
            logger.error(f"Error en GenerateSensorView: {str(e)}")
            logger.error(f"Datos JSON recibidos: {values_json}")
            return HttpResponse(f'Error generando el gráfico: {str(e)}')

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