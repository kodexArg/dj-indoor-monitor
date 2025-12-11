from datetime import timedelta, datetime
import pandas as pd
from django.utils import timezone
from django.db.models import Avg, Func
from django.db.models.functions import TruncSecond, TruncMinute, TruncHour, TruncDay
from .models import DataPoint, Sensor
from loguru import logger
import numpy as np
from collections import OrderedDict

TIMEFRAME_MAP = {
    '5S': '5S',
    '1T': '1min',
    '30T': '30min',
    '1H': '1h',
    '4H': '4h',
    '1D': '1D'
}

METRIC_MAP = {
    't': 'Temperatura',
    'h': 'Humedad',
    's': 'Sustrato',
    'l': 'Luz'
}

METRICS_CFG = {
    't': {
        'steps': [18, 24, 40],
        'unit': '°C',
        'title': 'Temperatura',
        'color_bars_gradient': [
            'rgba(135, 206, 235, 0.8)',
            'rgba(144, 238, 144, 0.6)',
            'rgba(255, 99, 71, 0.8)',
        ],
        'brand_color': '#dc3545',
    },
    'h': {
        'steps': [40, 55, 100],
        'unit': '%HR',
        'title': 'Humedad',
        'color_bars_gradient': [
            'rgba(255, 198, 109, 0.8)',
            'rgba(152, 251, 152, 0.6)',
            'rgba(100, 149, 237, 0.8)',
        ],
        'brand_color': '#1f77b4',
    },
    'l': {
        'steps': [0, 900, 1000],
        'unit': 'lum',
        'title': 'Luz',
        'color_bars_gradient': [
            'rgba(105, 105, 105, 0.2)',
            'rgba(255, 255, 153, 0.6)'
        ],
        'brand_color': '#ffc107',
    },
    's': {
        'steps': [0, 30, 60, 100],
        'unit': '%H',
        'title': 'Sustrato',
        'color_bars_gradient': [
            'rgba(255, 198, 109, 0.8)',
            'rgba(152, 251, 152, 0.6)',
            'rgba(100, 149, 237, 0.8)',
        ],
        'brand_color': '#28a745',
    }
}

INTERACTIVE_CHART_METRIC_NAMES = {
    't': 'Temperatura (°C)',
    'h': 'Humedad (%)',
    'l': 'Luz (lux)',
    's': 'Sustrato (%)'
}

INTERACTIVE_CHART_BAND_CFG = {
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

def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.lower()
        if value in ('true', '1', 't', 'y', 'yes'):
            return True
        elif value in ('false', '0', 'f', 'n', 'no'):
            return False
    if isinstance(value, int):
        return bool(value)
    return False


def get_timedelta_from_timeframe(timeframe):
    time_windows = {
        '5S': timedelta(minutes=3, seconds=45),
        '1T': timedelta(minutes=45),
        '30T': timedelta(hours=9),
        '1H': timedelta(hours=18),
        '4H': timedelta(days=3),
        '1D': timedelta(days=10, hours=12)
    }
    return time_windows[timeframe.upper()]

def get_start_date(timeframe, end_date):
    timeframe = timeframe.upper()
    
    if timeframe == '1MIN' or timeframe == '1M':
        timeframe = '1T'
    elif timeframe == '30MIN' or timeframe == '30M':
        timeframe = '30T'
        
    try:
        time_delta = get_timedelta_from_timeframe(timeframe)
        logger.debug(f"get_start_date: Using timeframe {timeframe}, window is {time_delta}")
        return end_date - time_delta
    except KeyError:
        logger.warning(f"get_start_date: Unrecognized timeframe '{timeframe}', defaulting to 1T")
        return end_date - timedelta(hours=3)

def normalize_timeframe(timeframe):
    return timeframe.lower().replace('t', 'min').lower()

def create_timeframed_dataframe(data_points, timeframe, start_date, end_date):
    normalized_tf = normalize_timeframe(timeframe)
    full_date_range = pd.date_range(start=start_date, end=end_date, freq=normalized_tf)

    df_calendar = pd.DataFrame({'timestamp': full_date_range, 'value': pd.NA})
    
    df_datapoints = pd.DataFrame(list(data_points.values('timestamp', 'value')))
    df_datapoints['timestamp'] = pd.to_datetime(df_datapoints['timestamp'], utc=True)
    
    if not df_datapoints.empty:
        df_datapoints = df_datapoints.sort_values('timestamp')
        df_calendar_sorted = df_calendar.sort_values('timestamp').rename(columns={'timestamp': 'calendar'})
        df_datapoints['calendar'] = pd.merge_asof(
            df_datapoints[['timestamp']],
            df_calendar_sorted[['calendar']],
            left_on='timestamp',
            right_on='calendar',
            direction='backward'
        )['calendar']
        df_datapoints = df_datapoints.groupby('calendar', as_index=False)['value'].mean()
        df_datapoints['value'] = df_datapoints['value'].apply(lambda x: round(x, 1))
        
    df_result = pd.merge(df_calendar, df_datapoints, left_on='timestamp', right_on='calendar', how='left', suffixes=('', '_agg'))
    df_result['value'] = df_result['value_agg'].combine_first(df_result['value'])
    df_result.drop('value_agg', axis=1, inplace=True)
    df_result = df_result.reset_index(drop=True)
    
    return df_result

def pretty_datetime(date):
    return date.strftime("%d/%m/%Y %H:%M")

def calculate_vpd(t, h):
    """Calcula Déficit de Presión de Vapor (VPD) en kPa."""
    # Fórmula de VPD: svp (presión de vapor de saturación) - vp (presión de vapor actual)
    svp = 0.6108 * np.exp((17.27 * t) / (t + 237.3)) # Ecuación de Tetens para SVP en kPa
    vp = svp * (h / 100) # VP actual basada en humedad relativa
    return svp - vp

def get_actual_timedelta_from_string(timeframe_str: str) -> timedelta:
    timeframe_str = str(timeframe_str).upper()
    try:
        if 'S' in timeframe_str:
            return timedelta(seconds=int(timeframe_str.replace('S', '')))
        elif 'T' in timeframe_str:  # Pandas convention for minutes
            return timedelta(minutes=int(timeframe_str.replace('T', '')))
        elif 'MIN' in timeframe_str: # Explicit minutes
            return timedelta(minutes=int(timeframe_str.replace('MIN', '')))
        elif 'H' in timeframe_str:
            return timedelta(hours=int(timeframe_str.replace('H', '')))
        elif 'D' in timeframe_str:
            return timedelta(days=int(timeframe_str.replace('D', '')))
        else:
            logger.warning(f"get_actual_timedelta_from_string: Unsupported timeframe string format: {timeframe_str}. Defaulting to 1 hour.")
            return timedelta(hours=1)
    except ValueError:
        logger.error(f"get_actual_timedelta_from_string: Could not parse int from timeframe string: {timeframe_str}. Defaulting to 1 hour.")
        return timedelta(hours=1)

def get_minimum_data_cutoff_date(timeframe_str: str, end_date: datetime, multiplier: int = 5) -> datetime:
    if not isinstance(end_date, datetime):
        logger.error(f"get_minimum_data_cutoff_date: end_date is not a datetime object. Got {type(end_date)}. Using timezone.now().")
        end_date = timezone.now()
        
    actual_delta = get_actual_timedelta_from_string(timeframe_str)
    total_delta = actual_delta * multiplier
    return end_date - total_delta

def get_active_sensor_names(timeframe_str: str, end_date: datetime, metrics_list: list = None, initial_sensor_names: list = None) -> list:
    minimum_cutoff = get_minimum_data_cutoff_date(timeframe_str, end_date, multiplier=5)
    logger.debug(f"get_active_sensor_names: Calculated minimum_cutoff_date: {minimum_cutoff} for timeframe {timeframe_str}")

    active_data_points = DataPoint.objects.filter(timestamp__gte=minimum_cutoff)

    if metrics_list:
        active_data_points = active_data_points.filter(metric__in=metrics_list)
        logger.debug(f"get_active_sensor_names: Filtering by metrics: {metrics_list}")

    if initial_sensor_names:
        active_data_points = active_data_points.filter(sensor__in=initial_sensor_names)
        logger.debug(f"get_active_sensor_names: Filtering by initial_sensor_names: {len(initial_sensor_names)} sensors")
    
    distinct_sensor_names = list(active_data_points.values_list('sensor', flat=True).distinct())
    logger.debug(f"get_active_sensor_names: Found {len(distinct_sensor_names)} active sensors: {distinct_sensor_names}")
    
    return distinct_sensor_names

class DataPointDataFrameBuilder:
    def __init__(self, timeframe='1T', start_date=None, end_date=None, metrics=None, pivot_metrics=False, use_last=False, add_room_information=False):
        self.timeframe = timeframe
        self.end_date = end_date if end_date else timezone.now()
        self.start_date = start_date if start_date else self._get_default_start_date()
        self.metrics = metrics
        self.pivot_metrics = pivot_metrics
        self.use_last = use_last
        self.add_room_information = add_room_information

    def _get_default_start_date(self):
        if self.timeframe:
            time_delta = get_timedelta_from_timeframe(self.timeframe)
            return self.end_date - time_delta
        else:
            return self.end_date - timedelta(days=365)

    def _get_db_trunc_kind(self, timeframe):
        """Determina el tipo de truncamiento de base de datos basado en el timeframe."""
        tf = timeframe.lower()
        if 's' in tf: return 'second'
        if 'min' in tf or 't' in tf: return 'minute'
        if 'h' in tf: return 'hour'
        if 'd' in tf: return 'day'
        return 'minute' # Default safe fallback

    def _get_data_points_values(self, datapoint_qs=None):
        queryset = datapoint_qs if datapoint_qs is not None else DataPoint.objects.all()
        
        queryset = queryset.filter(timestamp__gte=self.start_date, timestamp__lte=self.end_date)
        if self.metrics is not None:
            queryset = queryset.filter(metric__in=self.metrics)
        
        logger.debug(f"DataPointDataFrameBuilder: Querying for metrics {self.metrics} from {self.start_date} to {self.end_date}")
        
        # Optimization: Use DB aggregation instead of fetching all rows
        trunc_kind = self._get_db_trunc_kind(self.timeframe)
        
        # Mapping for dynamic Trunc class
        trunc_classes = {
            'second': TruncSecond,
            'minute': TruncMinute,
            'hour': TruncHour,
            'day': TruncDay
        }
        TruncClass = trunc_classes.get(trunc_kind, TruncMinute)

        logger.debug(f"DataPointDataFrameBuilder: Using DB aggregation with {trunc_kind}")

        aggregated_qs = queryset.annotate(
            period=TruncClass('timestamp')
        ).values('period', 'sensor', 'metric').annotate(
            value=Avg('value')
        ).order_by('period')
        
        # Log count of aggregated rows vs potential raw rows (estimated)
        # Note: count() on aggregated query returns number of groups
        count = aggregated_qs.count() 
        logger.debug(f"DataPointDataFrameBuilder: Retrieved {count} aggregated data points from DB")
        
        # Convert to list and rename 'period' to 'timestamp' to match expected interface
        values = []
        for item in aggregated_qs:
            values.append({
                'timestamp': item['period'],
                'sensor': item['sensor'],
                'metric': item['metric'],
                'value': item['value']
            })
            
        return values

    def _pivot_by_metrics(self, aggregated_df):
        logger.debug(f"_pivot_by_metrics: Input DataFrame shape: {aggregated_df.shape}")
        logger.debug(f"_pivot_by_metrics: Input DataFrame index levels: {aggregated_df.index.names}")
        
        if aggregated_df.empty:
            logger.warning("_pivot_by_metrics: Input DataFrame is empty, returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            pivot_df = aggregated_df.unstack(level='metric')
            logger.debug(f"_pivot_by_metrics: After unstack, pivot_df shape: {pivot_df.shape}")
            
            if isinstance(pivot_df.columns, pd.MultiIndex):
                logger.debug(f"_pivot_by_metrics: Column levels: {pivot_df.columns.names}")
                logger.debug(f"_pivot_by_metrics: Column values: {pivot_df.columns.tolist()}")
            else:
                logger.debug(f"_pivot_by_metrics: Columns: {pivot_df.columns.tolist()}")

            if isinstance(pivot_df.columns, pd.MultiIndex):
                pivot_df.columns = [col[1] for col in pivot_df.columns]
                logger.debug(f"_pivot_by_metrics: After column simplification: {pivot_df.columns.tolist()}")
            else:
                logger.warning("_pivot_by_metrics: Expected MultiIndex for columns but got simple Index")

            pivot_df.columns.name = None

            return pivot_df
        except Exception as e:
            logger.error(f"_pivot_by_metrics: Error during pivoting: {str(e)}")
            return pd.DataFrame()

    def build(self, datapoint_qs=None):
        logger.debug(f"DataPointDataFrameBuilder.build: Building DataFrame with timeframe={self.timeframe}, metrics={self.metrics}")
        
        # NOTE: self.use_last handling was removed in optimization for simplicity as it wasn't primary path for charts
        # If use_last is needed, we should query separately.
        
        data = self._get_data_points_values(datapoint_qs=datapoint_qs)
        df = pd.DataFrame(data)
        
        if df.empty:
            logger.warning("DataPointDataFrameBuilder.build: No data found, returning empty DataFrame")
            return df

        logger.debug(f"DataPointDataFrameBuilder.build: Initial DataFrame has {len(df)} rows with columns {df.columns.tolist()}")
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Since data is already aggregated by DB to the nearest unit (e.g. minute), 
        # we might still need to resample if the requested timeframe is '5T' but we aggregated to '1T'.
        # However, the volume is already small enough that Pandas is fast.
        
        try:
            if self.pivot_metrics:
                logger.debug("DataPointDataFrameBuilder.build: Using pivot_metrics approach")
                # We still group by to ensure exact alignment with requested timeframe (e.g. 5T)
                aggregated_df = df.groupby(
                    ['sensor', 'metric', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value']].mean()
                
                logger.debug(f"DataPointDataFrameBuilder.build: Aggregated DataFrame has shape {aggregated_df.shape}")
                df = self._pivot_by_metrics(aggregated_df)
                
                if df.empty:
                    logger.warning("DataPointDataFrameBuilder.build: Pivoted DataFrame is empty")
                else:
                    logger.debug(f"DataPointDataFrameBuilder.build: Pivoted DataFrame has shape {df.shape} and columns {df.columns.tolist()}")
                
                df = df.reset_index()
            else:
                logger.debug("DataPointDataFrameBuilder.build: Using standard groupby approach")
                # Fix: Include 'metric' in groupby to avoid aggregating string column 'metric' with mean
                # and to keep the data properly structured.
                agg_func = 'last' if self.use_last else 'mean'
                aggregated_df = df.groupby(
                    ['sensor', 'metric', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value']].agg(agg_func)
                df = aggregated_df.reset_index()
            
            if df.empty:
                logger.warning("DataPointDataFrameBuilder.build: Final DataFrame is empty")
            else:
                logger.debug(f"DataPointDataFrameBuilder.build: Final DataFrame has {len(df)} rows with columns {df.columns.tolist()}")
                if len(df) > 0:
                    logger.debug(f"DataPointDataFrameBuilder.build: First row sample: {df.iloc[0].to_dict()}")
            
            if self.add_room_information and not df.empty and 'sensor' in df.columns:
                logger.debug("DataPointDataFrameBuilder.build: Adding room information to DataFrame.")
                sensors_map_qs = Sensor.objects.select_related('room').all()
                sensor_to_room_map_internal = {s.name: s.room.name if s.room else "No Room" for s in sensors_map_qs}
                df['room'] = df['sensor'].apply(lambda s: sensor_to_room_map_internal.get(s, "No Room"))
                logger.debug(f"DataPointDataFrameBuilder.build: DataFrame with room info has columns {df.columns.tolist()}")

            return df
        except Exception as e:
            logger.error(f"DataPointDataFrameBuilder.build: Error building DataFrame: {str(e)}")
            return pd.DataFrame()

    def group_by_room(self, latest=False, sensors=True):
        df = self.build()

        sensores = Sensor.objects.all()
        sensor_room_map = {sensor.name: sensor.room.name if sensor.room else None for sensor in sensores}

        df['room'] = df['sensor'].apply(lambda sensor: sensor_room_map.get(sensor, ''))

        if latest:
            df = df.sort_values(by=['timestamp'], ascending=False).groupby('sensor').head(1)

        if not sensors:
            df = df.drop('sensor', axis=1, errors='ignore')
            df = df.groupby('room').mean()

        df_grouped = df.groupby('room')
        return df_grouped

def calculate_optimal_frequency(total_seconds, target_points):
    seconds_per_point = total_seconds / target_points
    
    if seconds_per_point < 1: return '1s'
    if seconds_per_point < 5: return f"{int(round(seconds_per_point))}s"
    if seconds_per_point < 60: return f"{int(round(seconds_per_point/5)*5)}s"
    if seconds_per_point < 300: return f"{int(round(seconds_per_point/60))}min"
    if seconds_per_point < 3600: return f"{int(round(seconds_per_point/300)*5)}min"
    if seconds_per_point < 86400: return f"{int(round(seconds_per_point/3600))}h"
    return f"{int(round(seconds_per_point/86400))}d"

def prepare_vpd_chart_data(df_grouped_chart):
    data_for_chart = []
    if df_grouped_chart is not None:
        for room, group in df_grouped_chart:
            if 't' in group.columns and 'h' in group.columns:
                avg_t = group['t'].mean()
                avg_h = group['h'].mean()
                if pd.notna(avg_t) and pd.notna(avg_h):
                    data_for_chart.append((room, avg_t, avg_h))
    return data_for_chart

def prepare_sensors_view_data(start_date, end_date, metric_map, metric_order, sensors_qs, datapoint_qs):
    data = {}
    all_sensor_metrics = {}
    sensor_names = [sensor.name for sensor in sensors_qs if sensor.room]

    if sensor_names:
        metrics_by_sensor_values = datapoint_qs.filter(
            sensor__in=sensor_names,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('sensor', 'metric').distinct()
        
        for item in metrics_by_sensor_values:
            sensor_name = item['sensor']
            metric = item['metric']
            if sensor_name not in all_sensor_metrics:
                all_sensor_metrics[sensor_name] = set()
            all_sensor_metrics[sensor_name].add(metric)
    
    for sensor in sensors_qs:
        if not sensor.room:
            continue
            
        room_name = sensor.room.name
        if room_name not in data:
            data[room_name] = {}

        sensor_metrics = all_sensor_metrics.get(sensor.name, set())
        
        if not sensor_metrics:
            logger.debug(f"Sensor '{sensor.name}' en sala '{room_name}' no tiene datos en el rango de tiempo.")
            continue

        ordered_metrics_for_sensor = OrderedDict()
        for metric_code in metric_order:
            if metric_code in sensor_metrics:
                ordered_metrics_for_sensor[metric_code] = None

        for metric_code in sorted(sensor_metrics):
            if metric_code not in ordered_metrics_for_sensor:
                ordered_metrics_for_sensor[metric_code] = None

        for metric_code in ordered_metrics_for_sensor:
            metric_full_name = metric_map.get(metric_code, metric_code)
            if metric_code not in data[room_name]:
                data[room_name][metric_code] = {
                    'metric': metric_code,
                    'metric_name': metric_full_name,
                    'sensors': []
                }
            if sensor.name not in data[room_name][metric_code]['sensors']:
                data[room_name][metric_code]['sensors'].append(sensor.name)

    for room_name, room_data in data.items():
        ordered_room_data = OrderedDict()
        for metric_code in metric_order:
            if metric_code in room_data:
                ordered_room_data[metric_code] = room_data[metric_code]
        for metric_code in room_data:
            if metric_code not in ordered_room_data:
                ordered_room_data[metric_code] = room_data[metric_code]
        data[room_name] = ordered_room_data
        
    return data

def prepare_gauges_view_data(cutoff_date, sensors_qs, datapoint_qs):
    latest_data_points_values = datapoint_qs.filter(timestamp__gte=cutoff_date).order_by(
        'sensor', 'metric', '-timestamp'
    ).distinct('sensor', 'metric').values('sensor', 'metric', 'value', 'timestamp')

    sensors_dict = {sensor.name: sensor for sensor in sensors_qs.select_related('room')}

    gauges_by_room = {}
    for data_point_values in latest_data_points_values:
        sensor_obj = sensors_dict.get(data_point_values['sensor'])
        if sensor_obj:
            room_name = sensor_obj.room.name if sensor_obj.room else "No Room"
            if room_name not in gauges_by_room:
                gauges_by_room[room_name] = []

            gauges_by_room[room_name].append({
                'value': data_point_values['value'],
                'metric': data_point_values['metric'],
                'sensor_name': data_point_values['sensor'],
                'timestamp': data_point_values['timestamp'].isoformat() if data_point_values['timestamp'] else None,
            })

    for room_name, gauges in gauges_by_room.items():
        gauges.sort(key=lambda x: (x['metric'], x['sensor_name']))
    
    return gauges_by_room

def prepare_vpd_table_data(start_date, end_date, metrics, sensors_qs, datapoint_qs_manager):
    table_builder = DataPointDataFrameBuilder(
        timeframe='5Min',
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        pivot_metrics=True,
        use_last=True
    )
    df_table = table_builder.build(datapoint_qs=datapoint_qs_manager)

    if df_table.empty:
        return pd.DataFrame()

    if 'timestamp' in df_table.columns:
        df_table['timestamp'] = pd.to_datetime(df_table['timestamp'])
    else:
        logger.warning("prepare_vpd_table_data: 'timestamp' column missing from df_table.")

    sensor_room_map = {sensor.name: sensor.room.name if sensor.room else "No Room" for sensor in sensors_qs}
    df_table['room'] = df_table['sensor'].apply(lambda s: sensor_room_map.get(s, "No Instalado"))
    
    if 't' in df_table.columns and 'h' in df_table.columns:
        df_table['vpd'] = df_table.apply(lambda row: calculate_vpd(row['t'], row['h']), axis=1)
    else:
        logger.warning("prepare_vpd_table_data: 't' or 'h' column missing, VPD calculation skipped.")
        df_table['vpd'] = pd.NA

    return df_table

def filter_dataframe_by_min_points(df, group_by_column, metrics, min_data_points_for_display, logger_instance):
    excluded_items_list = []

    if df.empty or group_by_column not in df.columns:
        logger_instance.warning(f"filter_dataframe_by_min_points: DataFrame is empty or missing '{group_by_column}' column.")
        return df.copy(), excluded_items_list 

    valid_items_to_plot = []
    for item_name, group_data in df.groupby(group_by_column):
        total_item_points = 0
        for metric_code in metrics:
            if metric_code in group_data.columns:
                total_item_points += group_data[metric_code].count()
        
        if total_item_points >= min_data_points_for_display:
            valid_items_to_plot.append(item_name)
        else:
            excluded_items_list.append(item_name)
            logger_instance.info(f"filter_dataframe_by_min_points: Excluding '{item_name}' due to insufficient data ({total_item_points} points)")
    
    if valid_items_to_plot:
        df_filtered = df[df[group_by_column].isin(valid_items_to_plot)].copy()
    else:
         logger_instance.warning("filter_dataframe_by_min_points: No items left to plot after filtering.")
         df_filtered = pd.DataFrame(columns=df.columns) 

    return df_filtered, sorted(excluded_items_list)