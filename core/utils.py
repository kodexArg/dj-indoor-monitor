from django.conf import settings
import pandas as pd
import plotly.graph_objs as go
from plotly.io import to_html
from datetime import datetime, timedelta, timezone
import pytz


def generate_plotly_chart(data: list, metric: str, start_date: datetime, end_date: datetime, selected_timeframe: str, div_id: str = 'chart') -> str:
    """Generate static Plotly chart HTML with the following features:
    - One line per sensor
    - Range slider for time navigation
    - Dotted grid
    - Legend positioned horizontally at the bottom
    - Unified hover mode for all series
    """
    if not data:
        return '<div id="' + div_id + '">No hay datos para mostrar</div>'
    
    # Crear DataFrame y asegurar que timestamp sea datetime64[ns, UTC]
    df = pd.DataFrame(data)
    # df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    # Convertir a timezone local después de asegurar que es UTC
    local_tz = pytz.timezone(settings.TIME_ZONE)
    start_date = start_date.astimezone(local_tz)
    end_date = end_date.astimezone(local_tz)
    
    # Adaptar dataframe
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)

    # agrupar df por timestamp según la freq
    timeframe_seconds = {
        '5s': 5,
        '30s': 5,
        '1min': 10,
        '10min': 100,
        '30min': 300,
        '1h': 600,
        '1d': 600 
    }
    
    seconds = timeframe_seconds.get(selected_timeframe.lower(), 5)  # default a 5 segundos
    resample_rule = f'{seconds}S'

    df = df.set_index('timestamp')
    grouped_df = df.groupby('sensor').resample(resample_rule).agg({
        metric: 'mean'
    })

    fig = go.Figure()
    
    for sensor in grouped_df.index.get_level_values('sensor').unique():
        sensor_data = grouped_df.loc[sensor]
        fig.add_trace(go.Scatter(
            x=sensor_data.index,
            y=sensor_data[metric],
            mode='lines',
            line_shape='spline',
            name=sensor
        ))
    
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
            range=[start_date, end_date],
            rangeslider=dict(
                visible=True,
                range=[start_date, end_date]
            ),
            showgrid=True,
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot',
            fixedrange=True
        ),
        hovermode='x unified'
    )
    
    return to_html(
        fig,
        include_plotlyjs=True, 
        full_html=False,
        div_id=div_id,
        config={'displayModeBar': False}
    )


def get_start_date(timeframe: str, end_date: datetime = None) -> datetime:
    time_windows = {
        '5s': timedelta(minutes=1),
        '30s': timedelta(minutes=6),
        '1min': timedelta(minutes=12),
        '10min': timedelta(minutes=120),
        '30min': timedelta(minutes=360),
        '1h': timedelta(hours=12),
        '1d': timedelta(days=288)
    }
    window = time_windows.get(timeframe.lower(), timedelta(minutes=15))
    return end_date - window
