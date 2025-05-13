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
        '5S': timedelta(minutes=3, seconds=45),   # 15 min / 4 = 3.75 min
        '1T': timedelta(minutes=45),              # 3 horas / 4 = 45 min
        '30T': timedelta(hours=9),                # 36 horas / 4 = 9 horas
        '1H': timedelta(hours=18),                # 3 días / 4 = 18 horas
        '4H': timedelta(days=3),                  # 12 días / 4 = 3 días
        '1D': timedelta(days=10, hours=12)        # 42 días / 4 = 10.5 días
    }
    return time_windows[timeframe.upper()]

def get_start_date(timeframe, end_date):
    """
    Calculate start date based on timeframe and end date.
    Uses the predefined time windows from get_timedelta_from_timeframe.
    """
    # Normalize timeframe format
    timeframe = timeframe.upper()
    
    # Handle potential variations in format
    if timeframe == '1MIN' or timeframe == '1M':
        timeframe = '1T'
    elif timeframe == '30MIN' or timeframe == '30M':
        timeframe = '30T'
        
    try:
        # Use the consistent time windows defined in get_timedelta_from_timeframe
        time_delta = get_timedelta_from_timeframe(timeframe)
        logger.debug(f"get_start_date: Using timeframe {timeframe}, window is {time_delta}")
        return end_date - time_delta
    except KeyError:
        # Default to 1 minute if timeframe not recognized
        logger.warning(f"get_start_date: Unrecognized timeframe '{timeframe}', defaulting to 1T")
        return end_date - timedelta(hours=3)  # Default is 3 hours for '1T'

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

def pretty_datetime(date):
    """
    Formatea una fecha en un formato corto (ej: 24/07/2024 14:55).
    """
    return date.strftime("%d/%m/%Y %H:%M")

class DataPointDataFrameBuilder:
    def __init__(self, timeframe='5S', start_date=None, end_date=None, metrics=None, pivot_metrics=False, use_last=False):
        self.timeframe = timeframe
        self.end_date = end_date if end_date else timezone.now()
        self.start_date = start_date if start_date else self._get_default_start_date()
        self.metrics = metrics
        self.pivot_metrics = pivot_metrics
        self.use_last = use_last

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
        
        logger.debug(f"DataPointDataFrameBuilder: Querying for metrics {self.metrics} from {self.start_date} to {self.end_date}")
        
        count = queryset.count()
        logger.debug(f"DataPointDataFrameBuilder: Found {count} raw data points")
        
        if self.use_last:
            queryset = queryset.order_by('sensor', 'metric', '-timestamp').distinct('sensor', 'metric')
            logger.debug(f"DataPointDataFrameBuilder: Using last values only, reduced to {queryset.count()} points")
        
        values = list(queryset.values())
        logger.debug(f"DataPointDataFrameBuilder: Retrieved {len(values)} data point values")
        return values

    def _pivot_by_metrics(self, aggregated_df):
        # Log the input aggregated dataframe shape and structure
        logger.debug(f"_pivot_by_metrics: Input DataFrame shape: {aggregated_df.shape}")
        logger.debug(f"_pivot_by_metrics: Input DataFrame index levels: {aggregated_df.index.names}")
        
        # Check if the DataFrame has any data
        if aggregated_df.empty:
            logger.warning("_pivot_by_metrics: Input DataFrame is empty, returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            # Paso 1: Desenrollar el índice 'metric' para que sus valores se conviertan en columnas.
            pivot_df = aggregated_df.unstack(level='metric')
            logger.debug(f"_pivot_by_metrics: After unstack, pivot_df shape: {pivot_df.shape}")
            
            # Log column MultiIndex structure
            if isinstance(pivot_df.columns, pd.MultiIndex):
                logger.debug(f"_pivot_by_metrics: Column levels: {pivot_df.columns.names}")
                logger.debug(f"_pivot_by_metrics: Column values: {pivot_df.columns.tolist()}")
            else:
                logger.debug(f"_pivot_by_metrics: Columns: {pivot_df.columns.tolist()}")

            # Paso 2: Simplificar los nombres de las columnas, extrayendo sólo la métrica (segundo elemento de la tupla).
            # Check if we have a MultiIndex first
            if isinstance(pivot_df.columns, pd.MultiIndex):
                # Extract the second level (metric) from each tuple
                pivot_df.columns = [col[1] for col in pivot_df.columns]
                logger.debug(f"_pivot_by_metrics: After column simplification: {pivot_df.columns.tolist()}")
            else:
                logger.warning("_pivot_by_metrics: Expected MultiIndex for columns but got simple Index")

            # Paso 3: Eliminar el nombre del índice de columnas para obtener un DataFrame limpio.
            pivot_df.columns.name = None

            return pivot_df
        except Exception as e:
            logger.error(f"_pivot_by_metrics: Error during pivoting: {str(e)}")
            # Return an empty DataFrame to prevent function failure
            return pd.DataFrame()

    def build(self):
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
                # Group by sensor, metric, and timestamp (using the specified timeframe)
                aggregated_df = df.groupby(
                    ['sensor', 'metric', pd.Grouper(key='timestamp', freq=self.timeframe)]
                )[['value']].mean()
                
                logger.debug(f"DataPointDataFrameBuilder.build: Aggregated DataFrame has shape {aggregated_df.shape}")
                df = self._pivot_by_metrics(aggregated_df)
                
                # Debug the pivoted dataframe
                if df.empty:
                    logger.warning("DataPointDataFrameBuilder.build: Pivoted DataFrame is empty")
                else:
                    logger.debug(f"DataPointDataFrameBuilder.build: Pivoted DataFrame has shape {df.shape} and columns {df.columns.tolist()}")
                
                df = df.reset_index()
            else:
                logger.debug("DataPointDataFrameBuilder.build: Using standard groupby approach")
                if self.use_last:
                    aggregated_df = df.groupby(
                        ['sensor', pd.Grouper(key='timestamp', freq=self.timeframe)]
                    )[['value', 'metric']].last()
                else:
                    aggregated_df = df.groupby(
                        ['sensor', pd.Grouper(key='timestamp', freq=self.timeframe)]
                    )[['value', 'metric']].mean()
                df = aggregated_df.reset_index()
            
            # Final DataFrame check
            if df.empty:
                logger.warning("DataPointDataFrameBuilder.build: Final DataFrame is empty")
            else:
                logger.debug(f"DataPointDataFrameBuilder.build: Final DataFrame has {len(df)} rows with columns {df.columns.tolist()}")
                # Sample data for debugging
                if len(df) > 0:
                    logger.debug(f"DataPointDataFrameBuilder.build: First row sample: {df.iloc[0].to_dict()}")
            
            return df
        except Exception as e:
            logger.error(f"DataPointDataFrameBuilder.build: Error building DataFrame: {str(e)}")
            return pd.DataFrame()

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

def interactive_plot(data_df, metric, by_room=False, timeframe='1h', start_date=None, end_date=None):
    """
    Genera un gráfico interactivo para múltiples sensores o salas.
    
    Args:
        data_df: DataFrame con los datos a graficar
        metric: Métrica a mostrar (t, h, l, s)
        by_room: Si es True, agrupa por sala en lugar de por sensor
        timeframe: Intervalo de tiempo para el eje X
        start_date: Fecha de inicio para el título
        end_date: Fecha de fin para el título
    
    Returns:
        HTML del gráfico, número de puntos graficados
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    if data_df.empty:
        return "<div class='no-data-alert'>No hay datos disponibles para este período</div>", 0
    
    # Configuración de colores según la métrica
    colors = {'t': '#FF5733', 'h': '#33A2FF', 'l': '#FFFF33', 's': '#33FF57'}
    
    # Texto para el título según la métrica
    metric_title = {
        't': 'Temperatura (°C)',
        'h': 'Humedad (%)',
        'l': 'Luz (lux)',
        's': 'Sustrato (%)'
    }.get(metric, metric)
    
    fig = make_subplots()
    
    # Agrupar por sala o mostrar todos los sensores
    plot_column = 'room' if by_room else 'sensor'
    
    # Contador de puntos graficados
    plotted_points = 0
    
    # Crear una línea para cada sensor/sala
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
    
    # Configurar el layout
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