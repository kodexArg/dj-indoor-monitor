from django.conf import settings
import pandas as pd
import plotly.graph_objs as go
from plotly.io import to_html
from datetime import datetime, timedelta, timezone


def generate_plotly_chart(data: list, metric: str, div_id: str = 'chart') -> str:
    """Generate static Plotly chart HTML with the following features:
    - One line per sensor
    - Range slider for time navigation
    - Dotted grid
    - Legend positioned horizontally at the bottom
    - Unified hover mode for all series
    """
    df = pd.DataFrame(data)
    if df.empty:
        return f'<div id="{div_id}"></div>'
    
    fig = go.Figure()
    

    """
    Create individual traces for each sensor with shared timestamp x-axis
    and metric-specific y-axis values
    """
    for sensor in df['sensor'].unique():
        sensor_df = df[df['sensor'] == sensor]
        fig.add_trace(go.Scatter(
            x=sensor_df['timestamp'],
            y=sensor_df[metric],
            mode='lines',
            line_shape='spline',  # Add this line to smooth the lines
            name=sensor
        ))
    

    """
    Layout configuration optimized for:
    - White background for better contrast
    - Horizontal legend inside chart
    - Minimal margins
    - Dynamic y-axis range with padding
    - Range slider and grid for better data exploration
    """
    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=True, 
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        margin=dict(
            l=0,
            r=0,
            t=5,
            b=8
        ),
        yaxis=dict(
            range=[df[metric].min() - 2, df[metric].max() + 2],
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot'
        ),
        xaxis=dict(
            rangeslider=dict(visible=True),
            showgrid=True,
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot'
        ),
        hovermode='x unified'
    )
    
    chart_html = to_html(
        fig,
        include_plotlyjs=True, 
        full_html=False,
        div_id=div_id,
        config={'displayModeBar': False}
    )
    
    return chart_html


def parse_time_string(time_str):
    """Convert time strings like '30s' or '1min' to seconds."""
    if time_str.endswith('m'):
        time_str = time_str.replace('m', 'min')
    elif time_str.endswith('s'):
        time_str = time_str.lower()
    
    try:
        return int(pd.Timedelta(time_str).total_seconds())
    except (ValueError, AttributeError):
        return 30


def timeframe_to_freq(timeframe: str) -> str:
    timeframe_to_freq = {
        '5s': '5s',
        '30s': '30s',
        '1m': '1min',
        '10m': '10min',
        '30m': '30min',
        '1h': '1H',
        '1d': '1D'
    }
    return timeframe_to_freq.get(timeframe, '30min')


def get_start_date(freq: str, end_date: datetime = None) -> datetime:
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    # Convert freq to seconds
    freq_seconds = {
        '5s': 5,
        '30s': 30,
        '1min': 60,
        '10min': 600,
        '30min': 1800,
        '1H': 3600,
        '1D': 86400
    }.get(freq.lower(), 1800)  # default 30min in seconds
    
    # Calculate total time window needed
    total_seconds = freq_seconds * settings.MAX_PLOT_RECORDS
    
    return end_date - timedelta(seconds=total_seconds)