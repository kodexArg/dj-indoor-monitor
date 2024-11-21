import pandas as pd

def process_chart_data(data: list, metric: str, freq: str = '3s') -> dict:
    """Process sensor data grouped by RPI with customizable intervals.
    
    Args:
        data (list): List of sensor data records containing timestamps and measurements
        metric (str): Metric to process, either 't' (temperature) or 'h' (humidity)
        freq (str, optional): Pandas time frequency string for grouping. Defaults to '30s'
    
    Returns:
        dict: Processed data with the structure {'data': [...]} where each item contains
              timestamp, rpi, and the averaged metric value for the specified interval
    """
    if metric not in ['t', 'h']:
        raise ValueError("metric must be either 't' for temperature or 'h' for humidity")

    df = pd.DataFrame(data)
    if df.empty:
        return {'data': []}
    
    # Convert timestamp and set as index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Group by RPI and time intervals
    grouped = df.groupby(['rpi', pd.Grouper(key='timestamp', freq=freq)]).agg({
        metric: 'mean'
    }).reset_index()
    
    # Format timestamps and round values
    grouped['timestamp'] = grouped['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    grouped[metric] = grouped[metric].round(1)
    
    return {'data': grouped.to_dict('records')}