from datetime import timedelta
import pandas as pd
from django.utils import timezone
from .models import DataPoint, Sensor
from loguru import logger

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
    """Convierte valor a booleano (string/int)."""
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
    """Convierte string de timeframe a timedelta (ej: '1H' a 18h)."""
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
    """Calcula fecha de inicio restando duración de timeframe a end_date."""
    timeframe = timeframe.upper()
    
    # Normalizar variaciones de timeframe
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
        return end_date - timedelta(hours=3) # Default: 3 horas para '1T'

def normalize_timeframe(timeframe):
    return timeframe.lower().replace('t', 'min').lower()

def create_timeframed_dataframe(data_points, timeframe, start_date, end_date):
    """Crea DataFrame con índice temporal completo y fusiona data_points agregados (media)."""
    normalized_tf = normalize_timeframe(timeframe)
    full_date_range = pd.date_range(start=start_date, end=end_date, freq=normalized_tf)

    df_calendar = pd.DataFrame({'timestamp': full_date_range, 'value': pd.NA})
    
    df_datapoints = pd.DataFrame(list(data_points.values('timestamp', 'value')))
    df_datapoints['timestamp'] = pd.to_datetime(df_datapoints['timestamp'], utc=True)
    
    if not df_datapoints.empty:
        df_datapoints = df_datapoints.sort_values('timestamp')
        df_calendar_sorted = df_calendar.sort_values('timestamp').rename(columns={'timestamp': 'calendar'})
        # Asignar cada datapoint a su 'bucket' de tiempo en df_calendar_sorted
        df_datapoints['calendar'] = pd.merge_asof(
            df_datapoints[['timestamp']],
            df_calendar_sorted[['calendar']],
            left_on='timestamp',
            right_on='calendar',
            direction='backward' # Asegura que se use el bucket anterior o igual
        )['calendar']
        df_datapoints = df_datapoints.groupby('calendar', as_index=False)['value'].mean()
        df_datapoints['value'] = df_datapoints['value'].apply(lambda x: round(x, 1))
        
    # Fusionar calendario con datos agrupados, manteniendo todos los timestamps del calendario
    df_result = pd.merge(df_calendar, df_datapoints, left_on='timestamp', right_on='calendar', how='left', suffixes=('', '_agg'))
    df_result['value'] = df_result['value_agg'].combine_first(df_result['value']) # Usar valor agregado si existe, sino el original (NA)
    df_result.drop('value_agg', axis=1, inplace=True)
    df_result = df_result.reset_index(drop=True)
    
    return df_result

def pretty_datetime(date):
    """Formatea datetime a 'DD/MM/YYYY HH:MM'."""
    return date.strftime("%d/%m/%Y %H:%M")

class DataPointDataFrameBuilder:
    """Construye DataFrames de DataPoint, con filtrado, pivoteo y agrupación."""
    def __init__(self, timeframe='5S', start_date=None, end_date=None, metrics=None, pivot_metrics=False, use_last=False):
        self.timeframe = timeframe
        self.end_date = end_date if end_date else timezone.now()
        self.start_date = start_date if start_date else self._get_default_start_date()
        self.metrics = metrics
        self.pivot_metrics = pivot_metrics
        self.use_last = use_last # Usar solo el último valor del periodo

    def _get_default_start_date(self):
        if self.timeframe:
            time_delta = get_timedelta_from_timeframe(self.timeframe)
            return self.end_date - time_delta
        else:
            return self.end_date - timedelta(days=365) # Default a un año si no hay timeframe

    def _get_data_points_values(self):
        queryset = DataPoint.objects.filter(timestamp__gte=self.start_date, timestamp__lte=self.end_date)
        if self.metrics is not None:
            queryset = queryset.filter(metric__in=self.metrics)
        
        logger.debug(f"DataPointDataFrameBuilder: Querying for metrics {self.metrics} from {self.start_date} to {self.end_date}")
        
        count = queryset.count()
        logger.debug(f"DataPointDataFrameBuilder: Found {count} raw data points")
        
        if self.use_last:
            # Optimización para obtener solo el último punto por sensor/métrica
            queryset = queryset.order_by('sensor', 'metric', '-timestamp').distinct('sensor', 'metric')
            logger.debug(f"DataPointDataFrameBuilder: Using last values only, reduced to {queryset.count()} points")
        
        values = list(queryset.values())
        logger.debug(f"DataPointDataFrameBuilder: Retrieved {len(values)} data point values")
        return values

    def _pivot_by_metrics(self, aggregated_df):
        """Pivota DataFrame agrupado, convirtiendo nivel 'metric' del índice en columnas."""
        logger.debug(f"_pivot_by_metrics: Input DataFrame shape: {aggregated_df.shape}")
        logger.debug(f"_pivot_by_metrics: Input DataFrame index levels: {aggregated_df.index.names}")
        
        if aggregated_df.empty:
            logger.warning("_pivot_by_metrics: Input DataFrame is empty, returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            pivot_df = aggregated_df.unstack(level='metric') # Mover 'metric' de índice a columnas
            logger.debug(f"_pivot_by_metrics: After unstack, pivot_df shape: {pivot_df.shape}")
            
            if isinstance(pivot_df.columns, pd.MultiIndex):
                logger.debug(f"_pivot_by_metrics: Column levels: {pivot_df.columns.names}")
                logger.debug(f"_pivot_by_metrics: Column values: {pivot_df.columns.tolist()}")
            else:
                logger.debug(f"_pivot_by_metrics: Columns: {pivot_df.columns.tolist()}")

            if isinstance(pivot_df.columns, pd.MultiIndex):
                pivot_df.columns = [col[1] for col in pivot_df.columns] # Simplificar nombres de columna (valor, métrica) -> métrica
                logger.debug(f"_pivot_by_metrics: After column simplification: {pivot_df.columns.tolist()}")
            else:
                logger.warning("_pivot_by_metrics: Expected MultiIndex for columns but got simple Index")

            pivot_df.columns.name = None # Limpiar nombre del índice de columnas

            return pivot_df
        except Exception as e:
            logger.error(f"_pivot_by_metrics: Error during pivoting: {str(e)}")
            return pd.DataFrame()

    def build(self):
        """Obtiene, agrega y procesa DataPoints según configuración, devolviendo DataFrame."""
        logger.debug(f"DataPointDataFrameBuilder.build: Building DataFrame with timeframe={self.timeframe}, metrics={self.metrics}")
        data = self._get_data_points_values()
        df = pd.DataFrame(data)
        
        if df.empty:
            logger.warning("DataPointDataFrameBuilder.build: No data found, returning empty DataFrame")
            return df

        logger.debug(f"DataPointDataFrameBuilder.build: Initial DataFrame has {len(df)} rows with columns {df.columns.tolist()}")
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        try:
            if self.pivot_metrics:
                logger.debug("DataPointDataFrameBuilder.build: Using pivot_metrics approach")
                # Agrupar por sensor, métrica y bucker de tiempo; calcular media.
                aggregated_df = df.groupby(
                    ['sensor', 'metric', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value']].mean()
                
                logger.debug(f"DataPointDataFrameBuilder.build: Aggregated DataFrame has shape {aggregated_df.shape}")
                df = self._pivot_by_metrics(aggregated_df)
                
                if df.empty:
                    logger.warning("DataPointDataFrameBuilder.build: Pivoted DataFrame is empty")
                else:
                    logger.debug(f"DataPointDataFrameBuilder.build: Pivoted DataFrame has shape {df.shape} and columns {df.columns.tolist()}")
                
                df = df.reset_index() # Restaurar 'timestamp' y 'sensor' como columnas
            else:
                logger.debug("DataPointDataFrameBuilder.build: Using standard groupby approach")
                agg_func = 'last' if self.use_last else 'mean'
                aggregated_df = df.groupby(
                    ['sensor', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value', 'metric']].agg(agg_func)
                df = aggregated_df.reset_index()
            
            if df.empty:
                logger.warning("DataPointDataFrameBuilder.build: Final DataFrame is empty")
            else:
                logger.debug(f"DataPointDataFrameBuilder.build: Final DataFrame has {len(df)} rows with columns {df.columns.tolist()}")
                if len(df) > 0:
                    logger.debug(f"DataPointDataFrameBuilder.build: First row sample: {df.iloc[0].to_dict()}")
            
            return df
        except Exception as e:
            logger.error(f"DataPointDataFrameBuilder.build: Error building DataFrame: {str(e)}")
            return pd.DataFrame()

    def group_by_room(self, latest=False, sensors=True):
        """Construye DataFrame, añade columna 'room' y agrupa por esta."""
        df = self.build()

        sensores = Sensor.objects.all()
        sensor_room_map = {sensor.name: sensor.room.name if sensor.room else None for sensor in sensores}

        df['room'] = df['sensor'].apply(lambda sensor: sensor_room_map.get(sensor, ''))

        if latest:
            df = df.sort_values(by=['timestamp'], ascending=False).groupby('sensor').head(1) # Último punto por sensor

        if not sensors:
            df = df.drop('sensor', axis=1, errors='ignore') # Eliminar columna sensor si no se necesita
            df = df.groupby('room').mean() # Promediar por sala

        df_grouped = df.groupby('room')
        return df_grouped

def interactive_plot(data_df, metric, by_room=False, timeframe='1h', start_date=None, end_date=None):
    """Genera gráfico interactivo Plotly (scatter) para una métrica, agrupable por sala/sensor."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    if data_df.empty:
        return "<div class='no-data-alert'>No hay datos disponibles para este período</div>", 0
    
    colors = {'t': '#FF5733', 'h': '#33A2FF', 'l': '#FFFF33', 's': '#33FF57'}
    
    metric_title = {
        't': 'Temperatura (°C)',
        'h': 'Humedad (%)',
        'l': 'Luz (lux)',
        's': 'Sustrato (%)'
    }.get(metric, metric)
    
    fig = make_subplots()
    
    plot_column = 'room' if by_room else 'sensor' # Columna para agrupar trazas
    
    plotted_points = 0
    
    for name, group in data_df.groupby(plot_column):
        if not group.empty and metric in group:
            plotted_points += len(group)
            fig.add_trace(
                go.Scatter(
                    x=group['timestamp'],
                    y=group[metric],
                    mode='lines+markers',
                    name=name,
                    line=dict(color=colors.get(metric, '#7F7F7F')),
                    hovertemplate=f"{name}: %{{y:.1f}}<extra></extra>"
                )
            )
    
    title_text = f"{metric_title} - {timeframe}"
    if start_date and end_date:
        title_text += f" ({start_date.strftime('%d/%m %H:%M')} - {end_date.strftime('%d/%m %H:%M')})"
    
    fig.update_layout(
        title=title_text,
        xaxis_title='Hora',
        yaxis_title=metric_title,
        template='plotly_dark',
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        hovermode='closest',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig.to_html(include_plotlyjs='cdn', full_html=False), plotted_points