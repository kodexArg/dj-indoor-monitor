from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from collections import OrderedDict
from .models import DataPoint, Sensor
from .charts import gauge_plot, sensor_plot, vpd_plot, generate_interactive_multi_metric_chart
from .utils import (
    get_timedelta_from_timeframe, 
    create_timeframed_dataframe,
    METRIC_MAP,
    DataPointDataFrameBuilder,
    pretty_datetime, 
    get_start_date, 
    to_bool, 
    calculate_optimal_frequency,
    filter_dataframe_by_min_points,
    calculate_vpd
)
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
        
        end_date = timezone.now()
        start_date = end_date - get_timedelta_from_timeframe(timeframe)

        data = {}
        sensors = Sensor.objects.select_related('room').all()
        
        all_sensor_metrics = {}
        sensor_names = [sensor.name for sensor in sensors if sensor.room]
        
        if sensor_names:
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
    TARGET_POINTS = 120
    MIN_DATA_POINTS_FOR_DISPLAY = 20

    def get_context_data(self, **kwargs):
        start_time = time.time()
        context = super().get_context_data(**kwargs)

        timeframe = self.request.GET.get('timeframe', '1T').lower()
        
        metrics_param = self.request.GET.get('metrics', self.request.GET.get('metric', 't'))
        metrics = [m.strip().lower() for m in metrics_param.split(',') if m.strip()] if metrics_param else ['t']
        if not metrics:
            metrics = ['t']
            
        room_grouping_active = to_bool(self.request.GET.get('room', 'false'))

        end_date = timezone.now()
        if end_date_str := self.request.GET.get('end_date'):
            try:
                end_date = timezone.datetime.fromisoformat(end_date_str)
            except ValueError:
                logger.warning(f"InteractiveView: Invalid end_date format: {end_date_str}")
        
        start_date = get_start_date(timeframe, end_date)
        if start_date_str := self.request.GET.get('start_date'):
            try:
                start_date = timezone.datetime.fromisoformat(start_date_str)
            except ValueError:
                logger.warning(f"InteractiveView: Invalid start_date format: {start_date_str}")
        
        logger.debug(f"InteractiveView: Time range: {start_date} to {end_date} ({timeframe})")

        df = self._fetch_sensor_data(metrics, start_date, end_date, room_grouping_active)
        
        group_by_column = 'room' if room_grouping_active else 'sensor'
        
        df_filtered, excluded_items_list = filter_dataframe_by_min_points(
            df, group_by_column, metrics, self.MIN_DATA_POINTS_FOR_DISPLAY, logger
        )

        chart_html, plotted_points = generate_interactive_multi_metric_chart(
            df_filtered, metrics, by_room=room_grouping_active, timeframe=timeframe, 
            start_date=start_date, end_date=end_date
        )
        
        time_window = get_timedelta_from_timeframe(timeframe)
        window_minutes = int(time_window.total_seconds() / 60)
        
        query_duration = time.time() - start_time
        metadata = {
            'timeframe': timeframe,
            'metrics': metrics,
            'start': start_date,
            'end': end_date,
            'start_pretty': pretty_datetime(start_date),
            'end_pretty': pretty_datetime(end_date),
            'record_count': len(df_filtered) if not df_filtered.empty else 0,
            'sensor_ids': list(df_filtered['sensor'].unique()) if not df_filtered.empty and 'sensor' in df_filtered and not room_grouping_active else [],
            'room_names': list(df_filtered['room'].unique()) if not df_filtered.empty and 'room' in df_filtered and room_grouping_active else [],
            'excluded_items': excluded_items_list,
            'window_minutes': window_minutes,
            'query_duration_s': round(query_duration, 3)
        }
        
        context.update({
            'metadata': metadata,
            'room': room_grouping_active,
            'chart_html': chart_html,
            'plotted_points': plotted_points,
            'target_points': self.TARGET_POINTS if not room_grouping_active else plotted_points
        })
        
        logger.info(f"InteractiveView: Completed in {query_duration:.3f}s with {plotted_points} points plotted. Excluded: {len(excluded_items_list)} items.")
        return context
    
    def _fetch_sensor_data(self, metrics, start_date, end_date, room_grouping_active):
        actual_time_window = end_date - start_date
        total_seconds_for_optimal_freq = actual_time_window.total_seconds()

        data_points_qs = DataPoint.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            metric__in=metrics
        ).order_by('timestamp')

        if not data_points_qs.exists():
            logger.debug("InteractiveView: No raw data points in time range.")
            return pd.DataFrame()
        
        logger.debug(f"InteractiveView: Found {data_points_qs.count()} raw data points in time range initially.")

        if room_grouping_active:
            logger.debug("InteractiveView: Room grouping active. Processing raw data for room averages.")
            raw_values = list(data_points_qs.values('timestamp', 'sensor', 'metric', 'value'))
            
            if not raw_values:
                return pd.DataFrame()
            
            df = pd.DataFrame(raw_values)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            sensors_map_qs = Sensor.objects.select_related('room').all()
            sensor_to_room_map_internal = {s.name: s.room.name if s.room else "No Room" for s in sensors_map_qs}
            df['room'] = df['sensor'].apply(lambda s: sensor_to_room_map_internal.get(s, "No Room"))
            df = df[df['room'] != "No Room"]

            if df.empty:
                logger.debug("InteractiveView: DataFrame empty after filtering for sensors with assigned rooms.")
                return pd.DataFrame()

            grouped_df = df.groupby(['room', 'timestamp', 'metric'])['value'].mean().reset_index()
            
            pivot_df = grouped_df.pivot_table(
                index=['room', 'timestamp'],
                columns='metric',
                values='value'
            ).reset_index()
            pivot_df.columns.name = None
            logger.debug(f"InteractiveView: Room grouping - returning pivoted data with shape {pivot_df.shape}")
            return pivot_df
        else:
            logger.debug("InteractiveView: Sensor grouping active. Using DataPointDataFrameBuilder.")
            actual_resampling_freq = calculate_optimal_frequency(total_seconds_for_optimal_freq, self.TARGET_POINTS)
            
            df_builder = DataPointDataFrameBuilder(
                timeframe=actual_resampling_freq, 
                start_date=start_date,
                end_date=end_date,
                metrics=metrics,
                pivot_metrics=True
            )
            df = df_builder.build() 
            
            if not df.empty and 'sensor' in df.columns:
                sensors_map_qs = Sensor.objects.select_related('room').all()
                sensor_to_room_map_internal = {s.name: s.room.name if s.room else "No Room" for s in sensors_map_qs}
                df['room'] = df['sensor'].apply(lambda s: sensor_to_room_map_internal.get(s, "No Room"))
            logger.debug(f"InteractiveView: Sensor grouping - returning DataFrame with shape {df.shape}")
            return df

