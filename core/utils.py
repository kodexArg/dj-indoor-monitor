from django.conf import settings
import pandas as pd
import plotly.graph_objs as go
from plotly.io import to_html


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


def process_chart_data(data: list, metric: str, freq: str = '30m') -> dict:
    """Process sensor data with time-based grouping and averaging.
    
    Handles data transformation for visualization including:
    - Timestamp conversion and grouping
    - Mean calculation per time interval
    - Value rounding and timestamp formatting
    - Limits the number of records according to MAX_PLOT_RECORDS setting
    """
    if metric not in ['t', 'h']:
        raise ValueError("metric must be either 't' for temperature or 'h' for humidity")

    df = pd.DataFrame(data)
    if df.empty:
        return {'data': []}
    

    """
    Data processing pipeline:
    1. Convert timestamps
    2. Group by sensor and time
    3. Calculate means
    4. Format output
    """
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    grouped = df.groupby(
        [
            'sensor',
            pd.Grouper(
                key='timestamp',
                freq=freq
            )
        ]
    ).agg(
        {
            metric: 'mean'
        }
    ).reset_index()
    
    grouped['timestamp'] = grouped['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    grouped[metric] = grouped[metric].round(1)
    
    # Ensure data is sorted by timestamp and sensor before limiting records
    grouped = grouped.sort_values(['timestamp', 'sensor'], ascending=[False, True])  # Modify this line to sort by timestamp descending
    grouped = grouped.tail(settings.MAX_PLOT_RECORDS)
    
    return {'data': grouped.to_dict('records')}


def parse_time_string(time_str):
    """Convert time strings like '30s' or '1T' to seconds."""
    if time_str.endswith('m'):
        time_str = time_str.replace('m', 'T')
    elif time_str.endswith('s'):
        time_str = time_str.lower()
    
    try:
        return int(pd.Timedelta(time_str).total_seconds())
    except (ValueError, AttributeError):
        return 30