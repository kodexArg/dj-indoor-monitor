from datetime import timedelta
import pandas as pd
import numpy as np
from django.utils import timezone
from .models import DataPoint, Sensor, Room

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
def to_bool(value):
    """
    Convierte un valor a booleano.
    """
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
    """
    Convierte un timeframe en su timedelta correspondiente.
    """
    time_windows = {
        '5S': timedelta(minutes=15),
        '1T': timedelta(hours=3),
        '30T': timedelta(hours=36),
        '1H': timedelta(days=3),
        '4H': timedelta(days=12),
        '1D': timedelta(days=42)
    }
    return time_windows[timeframe.upper()]

def get_start_date(timeframe, end_date):
    if timeframe == '5S':
        return end_date - pd.Timedelta(seconds=5)
    elif timeframe == '1T':
        return end_date - pd.Timedelta(minutes=1)
    elif timeframe == '30T':
        return end_date - pd.Timedelta(minutes=30)
    elif timeframe == '1H':
        return end_date - pd.Timedelta(hours=1)
    elif timeframe == '4H':
        return end_date - pd.Timedelta(hours=4)
    elif timeframe == '1D':
        return end_date - pd.Timedelta(days=1)
    else:
        return end_date - pd.Timedelta(hours=1)

def normalize_timeframe(timeframe):
    return timeframe.lower().replace('t', 'min').lower()

def create_timeframed_dataframe(data_points, timeframe, start_date, end_date):
    """
    Crea un DataFrame calendario (df_calendar) con todos los timestamps en el rango 
    [start_date, end_date] y valores iniciales nulos. Luego, agrupa (por mean) los valores 
    de data_points (df_datapoints) tras ajustar (floor) los timestamps para generar 
    df_result mediante merge.
    """
    normalized_tf = normalize_timeframe(timeframe)
    full_date_range = pd.date_range(start=start_date, end=end_date, freq=normalized_tf)

    # df_calendar (tabla base)
    df_calendar = pd.DataFrame({'timestamp': full_date_range, 'value': pd.NA})
    
    # df_datapoints (tabla de datos)
    df_datapoints = pd.DataFrame(list(data_points.values('timestamp', 'value')))
    df_datapoints['timestamp'] = pd.to_datetime(df_datapoints['timestamp'], utc=True)
    
    if not df_datapoints.empty:
        # Ordenamos ambos DataFrame
        df_datapoints = df_datapoints.sort_values('timestamp')
        df_calendar_sorted = df_calendar.sort_values('timestamp').rename(columns={'timestamp': 'calendar'})
        # Usamos merge_asof para asignar a cada datapoint la fecha de df_calendar
        df_datapoints['calendar'] = pd.merge_asof(
            df_datapoints[['timestamp']],
            df_calendar_sorted[['calendar']],
            left_on='timestamp',
            right_on='calendar',
            direction='backward'
        )['calendar']
        # Agrupamos usando la columna 'calendar'
        df_datapoints = df_datapoints.groupby('calendar', as_index=False)['value'].mean()
        df_datapoints['value'] = df_datapoints['value'].apply(lambda x: round(x, 1))
        
    # Merge para generar df_result.
    df_result = pd.merge(df_calendar, df_datapoints, left_on='timestamp', right_on='calendar', how='left', suffixes=('', '_agg'))
    df_result['value'] = df_result['value_agg'].combine_first(df_result['value'])
    df_result.drop('value_agg', axis=1, inplace=True)
    df_result = df_result.reset_index(drop=True)
    
    return df_result

class DataPointDataFrameBuilder:
    def __init__(self, timeframe='5S', start_date=None, end_date=None, metrics=None, pivot_metrics=False, use_last=False):
        self.timeframe = timeframe
        self.end_date = end_date if end_date else timezone.now()
        self.start_date = start_date if start_date else self._get_default_start_date()
        self.metrics = metrics
        self.pivot_metrics = pivot_metrics
        self.use_last = use_last # Restore use_last

    def _get_default_start_date(self):
        if self.timeframe:
            time_delta = get_timedelta_from_timeframe(self.timeframe)
            return self.end_date - time_delta
        else:
            return self.end_date - timedelta(days=365)

    def _get_data_points_values(self):
        queryset = DataPoint.objects.filter(timestamp__gte=self.start_date, timestamp__lte=self.end_date)
        if self.metrics is not None:
            queryset = queryset.filter(metric__in=self.metrics)
        if self.use_last:
            queryset = queryset.order_by('sensor', 'metric', '-timestamp').distinct('sensor', 'metric')
        return list(queryset.values())

    def _pivot_by_metrics(self, aggregated_df):
        # Paso 1: Desenrollar el índice 'metric' para que sus valores se conviertan en columnas.
        pivot_df = aggregated_df.unstack(level='metric')

        # Paso 2: Obtener la lista de métricas distintas registradas en la base de datos.
        distinct_metrics = list(DataPoint.objects.values_list('metric', flat=True).distinct())

        # Paso 3: Crear la estructura de columnas deseadas en forma de tuplas: ('value', métrica)
        desired_columns = [( 'value', m ) for m in distinct_metrics]

        # Paso 4: Reindexar el DataFrame para asegurarse de que aparezcan todas las métricas,
        # incluso si no todas están presentes en el agrupamiento actual.
        pivot_df = pivot_df.reindex(columns=desired_columns)

        # Paso 5: Simplificar los nombres de las columnas, extrayendo sólo la métrica (segundo elemento de la tupla).
        pivot_df.columns = [col[1] for col in pivot_df.columns]

        # Paso 6: Eliminar el nombre del índice de columnas para obtener un DataFrame limpio.
        pivot_df.columns.name = None

        return pivot_df

    def build(self):
        data = self._get_data_points_values()
        df = pd.DataFrame(data)
        if df.empty:
            return df

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        if self.pivot_metrics:
            if self.use_last:
                df = df.sort_values(by=['timestamp']).groupby('sensor').tail(1)
                aggregated_df = df.groupby(
                    ['sensor', 'metric', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value']].last()
            else:
                aggregated_df = df.groupby(
                    ['sensor', 'metric', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value']].mean()
            df = self._pivot_by_metrics(aggregated_df)
            df = df.reset_index()
        else:
            if self.use_last:
                aggregated_df = df.groupby(
                    ['sensor', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value', 'metric']].last()
            else:
                aggregated_df = df.groupby(
                    ['sensor', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value', 'metric']].mean()
            df = aggregated_df.reset_index()
        
        return df

    def group_by_room(self, latest=False, sensors=True):
        # Construye el DataFrame base utilizando el método build().
        df = self.build()

        sensores = Sensor.objects.all()
        sensor_room_map = {sensor.name: sensor.room.name if sensor.room else None for sensor in sensores}

        df['room'] = df['sensor'].apply(lambda sensor: sensor_room_map.get(sensor, ''))

        if latest:
            df = df.sort_values(by=['timestamp'], ascending=False).groupby('sensor').head(1)

        if not sensors:
            df = df.drop('sensor', axis=1, errors='ignore')
            df = df.groupby('room').mean()

        # Agrupa el DataFrame por la columna 'room'.
        df_grouped = df.groupby('room')
        return df_grouped