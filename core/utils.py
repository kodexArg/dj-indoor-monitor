import pandas as pd


def parse_time_string(time_str):
    """Convert time strings like '30s' or '1m' to seconds."""
    try:
        return int(pd.Timedelta(time_str).total_seconds())
    except (ValueError, AttributeError):
        return 30  # default fallback


def process_chart_data(data: list, metric: str, freq: str = '3s') -> dict:
    """Process sensor data grouped by sensor with customizable intervals."""
    if metric not in ['t', 'h']:
        raise ValueError("metric must be either 't' for temperature or 'h' for humidity")

    df = pd.DataFrame(data)
    if df.empty:
        return {'data': []}
    
    # Convert timestamp and set as index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Group by sensor and time intervals
    grouped = df.groupby(['sensor', pd.Grouper(key='timestamp', freq=freq)]).agg({
        metric: 'mean'
    }).reset_index()
    
    # Format timestamps and round values
    grouped['timestamp'] = grouped['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    grouped[metric] = grouped[metric].round(1)
    
    return {'data': grouped.to_dict('records')}