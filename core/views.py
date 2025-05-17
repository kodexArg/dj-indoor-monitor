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
    prepare_sensors_view_data,
    prepare_gauges_view_data,
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
        timeframe = self.request.GET.get('timeframe', '1h').lower()
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

        lookback_period_for_latest = timezone.timedelta(hours=24)
        start_date_for_latest = now - lookback_period_for_latest

        logger.debug(f"VPDView: Fetching latest 't' and 'h' data from the last {lookback_period_for_latest} for all sensors.")

        latest_data_points_qs = DataPoint.objects.filter(
            metric__in=['t', 'h'],
            timestamp__gte=start_date_for_latest,
            timestamp__lte=now
        ).order_by('sensor', 'metric', '-timestamp').distinct('sensor', 'metric')

        latest_data_values = list(latest_data_points_qs.values('sensor', 'metric', 'value', 'timestamp'))

        if not latest_data_values:
            logger.info(f"VPDView: No 't' or 'h' data points found for any sensor in the last {lookback_period_for_latest}.")
            context['room_data'] = []
            context['chart'] = vpd_plot([])
            return context
            
        df_latest_sensor_metrics = pd.DataFrame(latest_data_values)

        # Pivot to get t and h values side-by-side for each sensor
        df_sensor_th = df_latest_sensor_metrics.pivot_table(
            index='sensor',
            columns='metric',
            values='value'  # We only need the value for VPD calculation
        ).reset_index()
        df_sensor_th.columns.name = None # Remove the 'metric' name from columns index

        # Add room information
        unique_sensor_names_from_data = df_sensor_th['sensor'].unique()
        # Check if unique_sensor_names_from_data is not empty before querying Sensor model
        if not len(unique_sensor_names_from_data) > 0:
            logger.info("VPDView: No sensors found after pivoting latest t/h data. Table and chart will be empty.")
            context['room_data'] = []
            context['chart'] = vpd_plot([])
            return context

        sensors_qs_for_room_info = Sensor.objects.filter(name__in=unique_sensor_names_from_data).select_related('room')
        sensor_to_room_map = {s.name: s.room.name if s.room else "No Room" for s in sensors_qs_for_room_info}
        
        df_sensor_th['room'] = df_sensor_th['sensor'].map(sensor_to_room_map)
        df_sensor_th = df_sensor_th[df_sensor_th['room'] != "No Room"]

        # Ensure 't' and 'h' columns exist after pivot, then drop rows missing either
        if 't' not in df_sensor_th.columns:
            df_sensor_th['t'] = pd.NA
        if 'h' not in df_sensor_th.columns:
            df_sensor_th['h'] = pd.NA
        
        df_sensor_th.dropna(subset=['t', 'h'], inplace=True) # Keep only sensors with both t and h

        if df_sensor_th.empty:
            logger.info("VPDView: DataFrame is empty after filtering for sensors with both 't' and 'h' and room assignment.")
            context['room_data'] = []
            context['chart'] = vpd_plot([])
            return context

        # Calculate VPD for each sensor
        df_sensor_th['vpd'] = df_sensor_th.apply(lambda row: calculate_vpd(row['t'], row['h']), axis=1)
        
        # Data for the table (list of sensor dicts with room, sensor, t, h, vpd)
        context['room_data'] = df_sensor_th[['room', 'sensor', 't', 'h', 'vpd']].to_dict(orient='records')

        # Data for the chart (average t and h per room, from sensors that had valid VPD data)
        if df_sensor_th.empty: # Should be caught above, but defensive check
            data_for_chart = []
        else:
            df_room_level_for_chart = df_sensor_th.groupby('room').agg(
                avg_t=('t', 'mean'),
                avg_h=('h', 'mean')
            ).reset_index()

            data_for_chart = [
                (row['room'], row['avg_t'], row['avg_h'])
                for _, row in df_room_level_for_chart.iterrows()
                if pd.notna(row['avg_t']) and pd.notna(row['avg_h'])
            ]
        
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

        timeframe = self.request.GET.get('timeframe', '1h').lower()
        
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

