import pandas as pd
import plotly.graph_objs as go
from plotly.io import to_html


def parse_time_string(time_str):
    """Convert time strings like '30s' or '1m' to seconds."""
    try:
        return int(pd.Timedelta(time_str).total_seconds())
    except (ValueError, AttributeError):
        return 30  # default fallback


def process_chart_data(data: list, metric: str, freq: str = '30m') -> dict:
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


def generate_plotly_chart(data: list, metric: str, div_id: str = 'chart') -> str:
    """Generate static Plotly chart HTML."""
    df = pd.DataFrame(data)
    if df.empty:
        return f'<div id="{div_id}"></div>'
    
    fig = go.Figure()
    
    # Añadir trazas por sensor
    for sensor in df['sensor'].unique():
        sensor_df = df[df['sensor'] == sensor]
        fig.add_trace(go.Scatter(
            x=sensor_df['timestamp'],
            y=sensor_df[metric],
            mode='lines',
            name=sensor
        ))
    
    # Configurar layout
    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=True, 
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,  # Position legend inside the chart at the bottom
            xanchor='center',
            x=0.5
        ),
        margin=dict(
            l=10,
            r=10,
            t=10,
            b=10
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
        config={'displayModeBar': False}  # Deshabilitar controles de Plotly
    )
    
    return chart_html