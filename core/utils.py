from datetime import timedelta
import pandas as pd
import numpy as np

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
        
        print("\nDataFrame data_points ajustado y agrupado Describe:")
        print(df_datapoints.describe(include='all'))
    
    # Merge para generar df_result.
    df_result = pd.merge(df_calendar, df_datapoints, left_on='timestamp', right_on='calendar', how='left', suffixes=('', '_agg'))
    df_result['value'] = df_result['value_agg'].combine_first(df_result['value'])
    df_result.drop('value_agg', axis=1, inplace=True)
    df_result = df_result.reset_index(drop=True)
    
    print("\nDataFrame result Describe:")
    print(df_result.describe(include='all'))
    
    return df_result
