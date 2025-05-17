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
    calculate_vpd,
    process_room_grouped_data,
    prepare_vpd_chart_data,
    prepare_sensors_view_data,
    prepare_gauges_view_data,
    prepare_vpd_table_data,
    get_active_sensor_names
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
        
        context['gauges_by_room'] = prepare_gauges_view_data(
            cutoff_date, 
            Sensor.objects.all(), 
            DataPoint.objects
        )
        return context


class SensorsView(TemplateView):
    template_name = 'charts/sensors.html'
    metric_map = METRIC_MAP

    def get_context_data(self, **kwargs):
        start_time = time.time()
        
        context = super().get_context_data(**kwargs)
        timeframe = self.request.GET.get('timeframe', '4h').lower()
        context['timeframe'] = timeframe
        context['selected_timeframe'] = timeframe
        
        end_date = timezone.now()
        
        all_sensor_names_initially = list(Sensor.objects.values_list('name', flat=True))

        active_sensor_names = get_active_sensor_names(
            timeframe_str=timeframe, 
            end_date=end_date,
            metrics_list=None, 
            initial_sensor_names=all_sensor_names_initially
        )

        if not active_sensor_names:
            logger.info(f"SensorsView: No active sensors found for timeframe {timeframe}. Sensor list will be empty.")
            sensors_qs = Sensor.objects.none()
        else:
            logger.debug(f"SensorsView: Active sensors for timeframe {timeframe}: {active_sensor_names}")
            sensors_qs = Sensor.objects.select_related('room').filter(name__in=active_sensor_names)
        
        start_date_for_view_data = end_date - get_timedelta_from_timeframe(timeframe)

        data = prepare_sensors_view_data(
            start_date_for_view_data, 
            end_date, 
            self.metric_map, 
            [ 't', 'h', 'l', 's'],
            sensors_qs, 
            DataPoint.objects
        )

        context['data'] = data
        
        total_time = time.time() - start_time
        logger.debug(f"SensorsView: Renderizado en {total_time:.2f}s con {len(data)} sensores activos")

        return context

@method_decorator(csrf_exempt, name='dispatch')
class GenerateSensorView(View):
    def post(self, request):
        start_time = time.time()
        sensor_name = request.POST.get('sensor')
        timeframe = request.POST.get('timeframe', '4h').lower()
        metric = request.POST.get('metric', '')
        
        end_date = timezone.now()
        active_sensors = get_active_sensor_names(
            timeframe_str=timeframe,
            end_date=end_date,
            metrics_list=[metric] if metric else None,
            initial_sensor_names=[sensor_name]
        )

        if sensor_name not in active_sensors:
            logger.warning(f"Sensor {sensor_name} (metric: {metric}) has no recent data for timeframe {timeframe}. Not generating chart.")
            return HttpResponse(f"<div class='no-data-alert'>No hay datos suficientemente recientes para el sensor {sensor_name} ({metric}) según el timeframe seleccionado.</div>")
            
        start_date = timezone.now() - get_timedelta_from_timeframe(timeframe)
        
        data_points = DataPoint.objects.filter(
            sensor=sensor_name,
            metric=metric,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
        if not data_points.exists():
            logger.warning(f"No hay datos para sensor='{sensor_name}', metric='{metric}' en rango {timeframe} (post-activity check)")
            return HttpResponse(f"<div class='no-data-alert'>No hay datos disponibles para el sensor {sensor_name} ({metric}) en el período exacto.</div>")
        
        df = create_timeframed_dataframe(data_points, timeframe, start_date, end_date)
        chart_html, count = sensor_plot(df, sensor_name, metric, timeframe, start_date, end_date)
        
        total_time = time.time() - start_time
        logger.debug(f"Gráfico para {sensor_name}/{metric}: {count} puntos en {total_time:.2f}s")
        
        return HttpResponse(chart_html)


class VPDView(TemplateView):
    template_name = 'charts/vpd.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        minutes_ago = now - timezone.timedelta(minutes=15)

        vpd_timeframe_for_activity = '5Min'

        all_initial_sensor_names = list(Sensor.objects.values_list('name', flat=True))
        active_sensor_names_for_vpd = get_active_sensor_names(
            timeframe_str=vpd_timeframe_for_activity, 
            end_date=now,
            metrics_list=['t', 'h'],
            initial_sensor_names=all_initial_sensor_names
        )

        if not active_sensor_names_for_vpd:
            logger.info("VPDView: No active sensors with recent t/h data found. VPD table and chart will be empty.")
            context['room_data'] = []
            context['chart'] = vpd_plot([])
            return context

        logger.debug(f"VPDView: Active sensors for t/h data: {active_sensor_names_for_vpd}")
        
        sensors_for_table_qs = Sensor.objects.filter(name__in=active_sensor_names_for_vpd)

        datapoints_for_table_qs = DataPoint.objects.filter(sensor__in=active_sensor_names_for_vpd)

        df_table = prepare_vpd_table_data(
            start_date=minutes_ago, 
            end_date=now, 
            metrics=['t', 'h'], 
            sensors_qs=sensors_for_table_qs,
            datapoint_qs_manager=datapoints_for_table_qs
        )

        if df_table.empty:
            context['room_data'] = []
            context['chart'] = vpd_plot([]) 
            return context

        context['room_data'] = df_table.to_dict(orient='records')

        datapoints_for_chart_qs = DataPoint.objects.filter(sensor__in=active_sensor_names_for_vpd)
        chart_builder = DataPointDataFrameBuilder(
            timeframe='5Min',
            start_date=minutes_ago,
            end_date=now,
            metrics=['t', 'h'],
            pivot_metrics=True,
            use_last=True
        )
        df_for_chart_input = chart_builder.build(datapoint_qs=datapoints_for_chart_qs)
        
        df_grouped_chart = chart_builder.group_by_room()

        data_for_chart = prepare_vpd_chart_data(df_grouped_chart)
        
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

        timeframe = self.request.GET.get('timeframe', '4h').lower()
        
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

        df = self._fetch_sensor_data(metrics, start_date, end_date, room_grouping_active, timeframe)
        
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
    
    def _fetch_sensor_data(self, metrics, start_date, end_date, room_grouping_active, timeframe):
        actual_time_window = end_date - start_date
        total_seconds_for_optimal_freq = actual_time_window.total_seconds()

        current_timeframe_for_activity_check = timeframe

        active_sensor_names_list = get_active_sensor_names(
            timeframe_str=current_timeframe_for_activity_check,
            end_date=end_date,
            metrics_list=metrics
        )

        if not active_sensor_names_list:
            logger.info("InteractiveView._fetch_sensor_data: No active sensors found based on 5x timeframe rule. Returning empty DataFrame.")
            return pd.DataFrame()
        
        logger.debug(f"InteractiveView._fetch_sensor_data: Active sensors for query ({len(active_sensor_names_list)}): {active_sensor_names_list}")

        data_points_qs = DataPoint.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            metric__in=metrics,
            sensor__in=active_sensor_names_list
        ).order_by('timestamp')

        if not data_points_qs.exists():
            logger.debug("InteractiveView: No raw data points in time range for active sensors.")
            return pd.DataFrame()
        
        logger.debug(f"InteractiveView: Found {data_points_qs.count()} raw data points for active sensors in time range.")

        if room_grouping_active:
            sensors_map_qs = Sensor.objects.select_related('room').all()
            sensor_to_room_map_internal = {s.name: s.room.name if s.room else "No Room" for s in sensors_map_qs}
            df = process_room_grouped_data(data_points_qs, sensor_to_room_map_internal)
            logger.debug(f"InteractiveView: Room grouping - returning pivoted data with shape {df.shape if not df.empty else '(empty)'}")
            return df
        else:
            logger.debug("InteractiveView: Sensor grouping active. Using DataPointDataFrameBuilder.")
            actual_resampling_freq = calculate_optimal_frequency(total_seconds_for_optimal_freq, self.TARGET_POINTS)
            
            df_builder = DataPointDataFrameBuilder(
                timeframe=actual_resampling_freq, 
                start_date=start_date,
                end_date=end_date,
                metrics=metrics,
                pivot_metrics=True,
                add_room_information=True
            )
            df = df_builder.build(datapoint_qs=data_points_qs)
            
            logger.debug(f"InteractiveView: Sensor grouping - returning DataFrame with shape {df.shape if not df.empty else '(empty)'}")
            return df

