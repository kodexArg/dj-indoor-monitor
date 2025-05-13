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
from .utils import pretty_datetime, get_start_date, to_bool, interactive_plot
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
    TARGET_POINTS = 120  # Target number of points to display in the chart
    MIN_DATA_POINTS_FOR_DISPLAY = 20 # Minimum data points for a sensor/room to be displayed

    def get_context_data(self, **kwargs):
        start_time = time.time()
        context = super().get_context_data(**kwargs)

        # Extract and validate request parameters
        timeframe = self.request.GET.get('timeframe', '1T').lower()
        logger.debug(f"InteractiveView: Using timeframe: {timeframe}")
        
        metrics_param = self.request.GET.get('metrics', self.request.GET.get('metric', 't'))
        metrics = [m.strip().lower() for m in metrics_param.split(',') if m.strip()] if metrics_param else ['t']
        if not metrics:
            metrics = ['t']
        logger.debug(f"InteractiveView: Using metrics: {metrics}")
            
        room_grouping_active = to_bool(self.request.GET.get('room', 'true'))
        logger.debug(f"InteractiveView: Grouping by room: {room_grouping_active}")

        # Set time range
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

        # Fetch data
        df = self._fetch_sensor_data(timeframe, metrics, start_date, end_date)
        
        # Add room information for grouping
        sensors_map = Sensor.objects.select_related('room').all()
        sensor_to_room_map = {s.name: s.room.name if s.room else "No Room" for s in sensors_map}
        
        excluded_items_list = []
        df_filtered = pd.DataFrame()

        if not df.empty and 'sensor' in df.columns:
            df['room'] = df['sensor'].apply(lambda s: sensor_to_room_map.get(s, "No Room"))
            logger.debug(f"InteractiveView: Added room column, found {df['room'].nunique()} unique rooms")

            group_by_column = 'room' if room_grouping_active else 'sensor'
            
            valid_items_to_plot = []
            for item_name, group_data in df.groupby(group_by_column):
                total_item_points = 0
                for metric_code in metrics:
                    if metric_code in group_data.columns:
                        total_item_points += group_data[metric_code].count() # count non-NaN values
                
                if total_item_points >= self.MIN_DATA_POINTS_FOR_DISPLAY:
                    valid_items_to_plot.append(item_name)
                else:
                    excluded_items_list.append(item_name)
                    logger.info(f"InteractiveView: Excluding '{item_name}' due to insufficient data ({total_item_points} points)")
            
            if valid_items_to_plot:
                df_filtered = df[df[group_by_column].isin(valid_items_to_plot)]
            else:
                 logger.warning("InteractiveView: No items left to plot after filtering by MIN_DATA_POINTS_FOR_DISPLAY")
        
        else:
            logger.warning("InteractiveView: DataFrame is empty or missing 'sensor' column before filtering.")
            df_filtered = df # Pass empty or original df if it was problematic

        # Generate chart
        chart_html, plotted_points = self._generate_multi_metric_chart(
            df_filtered, metrics, by_room=room_grouping_active, timeframe=timeframe, 
            start_date=start_date, end_date=end_date
        )
        
        # Calculate time window from timeframe for context
        time_window = get_timedelta_from_timeframe(timeframe)
        window_minutes = int(time_window.total_seconds() / 60)
        
        # Prepare context data
        query_duration = time.time() - start_time
        metadata = {
            'timeframe': timeframe,
            'metrics': metrics,
            'start': start_date,
            'end': end_date,
            'start_pretty': pretty_datetime(start_date),
            'end_pretty': pretty_datetime(end_date),
            'record_count': len(df_filtered) if not df_filtered.empty else 0,
            'sensor_ids': list(df_filtered['sensor'].unique()) if not df_filtered.empty and 'sensor' in df_filtered else [],
            'excluded_items': sorted(excluded_items_list),
            'window_minutes': window_minutes,
            'query_duration_s': round(query_duration, 3)
        }
        
        context.update({
            'metadata': metadata,
            'room': room_grouping_active,
            'chart_html': chart_html,
            'plotted_points': plotted_points,
            'target_points': self.TARGET_POINTS
        })
        
        logger.info(f"InteractiveView: Completed in {query_duration:.3f}s with {plotted_points} points plotted. Excluded: {len(excluded_items_list)} items.")
        return context
    
    def _fetch_sensor_data(self, timeframe, metrics, start_date, end_date):
        """Fetch sensor data and return as DataFrame with pivoted metrics as columns."""
        time_window = get_timedelta_from_timeframe(timeframe)
        total_seconds = time_window.total_seconds()
        optimal_freq = self._calculate_optimal_frequency(total_seconds, self.TARGET_POINTS)
        
        logger.debug(f"InteractiveView: Total time window is {total_seconds} seconds")
        logger.debug(f"InteractiveView: Using sampling frequency '{optimal_freq}' for consistent point count")
        
        data_count = DataPoint.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            metric__in=metrics
        ).count()
        
        logger.debug(f"InteractiveView: Raw data points in time range: {data_count}")
        
        if data_count == 0:
            return pd.DataFrame()
        
        try:
            df = DataPointDataFrameBuilder(
                timeframe=optimal_freq, 
                start_date=start_date,
                end_date=end_date,
                metrics=metrics,
                pivot_metrics=True
            ).build()
            
            if not df.empty:
                logger.debug(f"InteractiveView: DataFrameBuilder returned {len(df)} rows with optimal frequency '{optimal_freq}'")
                return df
                
            logger.info("InteractiveView: DataFrameBuilder returned empty. Attempting direct pivot approach")
            raw_data = list(DataPoint.objects.filter(
                timestamp__gte=start_date,
                timestamp__lte=end_date,
                metric__in=metrics
            ).values('timestamp', 'sensor', 'metric', 'value'))
            
            if not raw_data:
                return pd.DataFrame()
                
            df = pd.DataFrame(raw_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['timestamp'] = df['timestamp'].dt.floor(optimal_freq)
            
            pivot_df = df.pivot_table(
                index=['timestamp', 'sensor'],
                columns='metric',
                values='value',
                aggfunc='mean'
            ).reset_index()
            
            if pivot_df.empty:
                return pd.DataFrame()
                
            logger.debug(f"InteractiveView: Direct pivot returned {len(pivot_df)} rows")
            return pivot_df
            
        except Exception as e:
            logger.error(f"InteractiveView: Error fetching data: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_optimal_frequency(self, total_seconds, target_points):
        """Calculate the optimal frequency to achieve the target number of points."""
        seconds_per_point = total_seconds / target_points
        
        if seconds_per_point < 1: return '1s'
        if seconds_per_point < 5: return f"{int(round(seconds_per_point))}s"
        if seconds_per_point < 60: return f"{int(round(seconds_per_point/5)*5)}s"
        if seconds_per_point < 300: return f"{int(round(seconds_per_point/60))}min"
        if seconds_per_point < 3600: return f"{int(round(seconds_per_point/300)*5)}min"
        if seconds_per_point < 86400: return f"{int(round(seconds_per_point/3600))}h"
        return f"{int(round(seconds_per_point/86400))}d"
    
    def _generate_multi_metric_chart(self, data_df, metrics, by_room=False, timeframe='1T', start_date=None, end_date=None):
        """Generate an interactive chart with multiple metrics."""
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import plotly.colors as pcolors
        
        if data_df.empty:
            logger.warning("_generate_multi_metric_chart: Empty DataFrame, returning no data message")
            return "<div class='no-data-alert'>No hay datos disponibles para este período o los sensores fueron filtrados.</div>", 0
        
        logger.debug(f"_generate_multi_metric_chart: Processing DataFrame with {len(data_df)} rows for chart generation.")
        
        base_colors = pcolors.qualitative.Plotly 
        metric_names = {
            't': 'Temperatura (°C)',
            'h': 'Humedad (%)',
            'l': 'Luz (lux)',
            's': 'Sustrato (%)'
        }
        
        # Define metric configuration for background bands
        metric_cfg = {
            't': {
                'steps': [18, 24, 40],
                'colors': ['rgba(135, 206, 235, 0.2)', 'rgba(144, 238, 144, 0.2)', 'rgba(255, 99, 71, 0.2)']
            },
            'h': {
                'steps': [40, 55, 100],
                'colors': ['rgba(255, 198, 109, 0.2)', 'rgba(152, 251, 152, 0.2)', 'rgba(100, 149, 237, 0.2)']
            },
            'l': {
                'steps': [0, 900, 1000],
                'colors': ['rgba(105, 105, 105, 0.1)', 'rgba(255, 255, 153, 0.2)']
            },
            's': {
                'steps': [0, 30, 60, 100],
                'colors': ['rgba(255, 198, 109, 0.2)', 'rgba(152, 251, 152, 0.2)', 'rgba(100, 149, 237, 0.2)']
            }
        }
        
        fig = make_subplots(
            rows=len(metrics), 
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.08, # Increased vertical spacing for better separation
            # subplot_titles removed as per request
        )
        
        group_column = 'room' if by_room else 'sensor'
        if group_column not in data_df.columns:
            logger.error(f"_generate_multi_metric_chart: Missing '{group_column}' column in DataFrame")
            return "<div class='no-data-alert'>Error: Columna de agrupación requerida ausente.</div>", 0
        
        plotted_points = 0
        unique_items = sorted(data_df[group_column].unique())
        color_map = {item_name: base_colors[i % len(base_colors)] for i, item_name in enumerate(unique_items)}

        logger.debug(f"_generate_multi_metric_chart: Plotting for {len(unique_items)} unique {group_column}s: {unique_items}")
        
        # Add background bands for each metric
        for i, metric_code in enumerate(metrics, 1):
            # Add background bands if configuration exists for this metric
            if metric_code in metric_cfg:
                steps = metric_cfg[metric_code]['steps']
                colors = metric_cfg[metric_code]['colors']
                
                # Add band for first section if it doesn't start at 0
                if steps[0] > 0:
                    fig.add_shape(
                        type="rect",
                        xref=f"x{i}",  # Revert to subplot x-axis data coordinates
                        yref=f"y{i}",
                        x0=start_date,  # Use actual start_date
                        x1=end_date,  # Use actual end_date
                        y0=0,
                        y1=steps[0],
                        fillcolor=colors[0],
                        opacity=0.5,
                        layer="below",
                        line_width=0,
                        row=i, col=1
                    )
                
                # Add bands for remaining sections
                for j in range(1, len(steps)):
                    fig.add_shape(
                        type="rect",
                        xref=f"x{i}",  # Revert to subplot x-axis data coordinates
                        yref=f"y{i}",
                        x0=start_date,  # Use actual start_date
                        x1=end_date,  # Use actual end_date
                        y0=steps[j-1],
                        y1=steps[j],
                        fillcolor=colors[min(j, len(colors)-1)],
                        opacity=0.5,
                        layer="below",
                        line_width=0,
                        row=i, col=1
                    )
            
            if metric_code not in data_df.columns:
                logger.warning(f"_generate_multi_metric_chart: Metric '{metric_code}' not in DataFrame columns: {data_df.columns.tolist()}")
                continue
                
            for item_name, group_data in data_df.groupby(group_column):
                valid_data = group_data.dropna(subset=[metric_code])
                if valid_data.empty:
                    continue
                    
                plotted_points += len(valid_data)
                item_color = color_map.get(item_name, '#808080') 
                
                fig.add_trace(
                    go.Scatter(
                        x=valid_data['timestamp'],
                        y=valid_data[metric_code],
                        mode='lines+markers',
                        name=f"{item_name} - {metric_names.get(metric_code, metric_code.upper())}",
                        line=dict(color=item_color, width=1.5),
                        marker=dict(size=4, color=item_color),
                        hovertemplate=f"{item_name} ({metric_names.get(metric_code, metric_code.upper())}): %{{y:.1f}}<extra></extra>"
                    ),
                    row=i, col=1
                )
        
        if plotted_points == 0:
            logger.warning("_generate_multi_metric_chart: No points plotted. DataFrame might be empty or all items filtered.")
            return "<div class='no-data-alert'>No hay datos para mostrar después del filtrado.</div>", 0
        
        fig.update_layout(
            title=None, 
            height=467 * len(metrics),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=80, r=80, t=50, b=50), # Increased right margin, balanced with left
            hovermode='closest',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                traceorder="normal"
            ),
            autosize=True, # Ensure autosize is on
            # width=1000 # Removed explicit width to rely more on autosize and responsive config
        )
        
        # Configure axes for all subplots
        for i in range(1, len(metrics) + 1):
            fig.update_xaxes(
                range=[start_date, end_date], # Explicitly set x-axis range
                showticklabels=True, 
                showgrid=True, gridwidth=1, gridcolor='rgba(211,211,211,0.5)', 
                showline=True, linewidth=1, linecolor='lightgreen', mirror=True,
                row=i, col=1,
                tickfont=dict(size=11) # Slightly larger tick font
            )
            
            # Configure Y-axis with ticks on both sides
            fig.update_yaxes(
                showgrid=True, 
                gridwidth=1, 
                gridcolor='rgba(211,211,211,0.5)', 
                showline=True, 
                linewidth=1, 
                linecolor='lightgreen', 
                mirror=True,  # Show axis line on both sides
                row=i, 
                col=1,
                tickfont=dict(size=11), # Slightly larger tick font
                tickformat=".1f", # Format tick values with one decimal place
                ticks="outside", # Show tick marks outside the axis
                showticklabels=True, # Show tick labels
            )
            
            if metrics[i-1] in metric_names:
                fig.update_yaxes(
                    title_text=metric_names[metrics[i-1]], 
                    title_standoff=15, # Add standoff to move title away from axis
                    title_font=dict(size=14, family="Arial, sans-serif", color="#5f9b62", weight="bold"),
                    row=i, 
                    col=1
                )
        
        # Remove X-axis title from the bottom-most subplot
        fig.update_xaxes(title_text=None, row=len(metrics), col=1)
        
        logger.debug(f"_generate_multi_metric_chart: Generated chart with {plotted_points} points")
        return fig.to_html(include_plotlyjs='cdn', full_html=False, config={
            'responsive': True,
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
        }), plotted_points

