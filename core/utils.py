from datetime import timedelta
import pandas as pd

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
    Creates a DataFrame from data points and groups it by the specified timeframe,
    returning a simple DataFrame with 'timestamp' and 'value' fields.
    Ensures all expected time points exist within the start and end dates,
    filling missing values with null.
    """
    # Normalize timeframe to be compatible with pandas
    timeframe = normalize_timeframe(timeframe)

    # Generate a complete date range based on the timeframe
    full_date_range = pd.date_range(start=start_date, end=end_date, freq=timeframe)
    
    # Create a DataFrame from the data points
    df = pd.DataFrame(list(data_points.values('timestamp', 'value')))

    if df.empty:
        # If there's no data, create an empty DataFrame with the full date range
        df_full = pd.DataFrame({'timestamp': full_date_range})
        df_full['value'] = pd.NA  # Fill all values with NA
        return df_full
    
    # Convert the timestamp column to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Group the data by the specified timeframe and calculate the mean
    df = df.groupby(pd.Grouper(key='timestamp', freq=timeframe))['value'].mean().reset_index()


    # Create a DataFrame from the full date range
    df_full = pd.DataFrame({'timestamp': full_date_range})

    # Merge the full date range DataFrame with the grouped data
    df = pd.merge(df_full, df, on='timestamp', how='right')

    # Fill any remaining missing values with NA
    df = df.fillna(pd.NA)

    df['value'] = df['value'].apply(lambda x: round(x, 1) if pd.notnull(x) else x)

    return df

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