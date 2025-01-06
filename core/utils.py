from typing import List, Tuple
from django.conf import settings
from datetime import datetime, timedelta, timezone
import pytz
import pandas as pd
import plotly.graph_objs as go
from plotly.io import to_html
from plotly.subplots import make_subplots


def old_devices_plot_generator(data: List[dict], start_date: datetime, end_date: datetime) -> str:
    """
    Genera un gráfico con subplots para temperatura y humedad, compartiendo la misma leyenda.

    Parámetros:
    - `data`: Lista de diccionarios con los datos del sensor.
    - `start_date`: Fecha de inicio del rango de datos.
    - `end_date`: Fecha de fin del rango de datos.

    Retorna:
    - str: HTML del gráfico generado.
    """
    if not data:
        return '<div>No hay datos para mostrar</div>'
    
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    
    df = df.set_index('timestamp')
    grouped_df = df.groupby('sensor').resample('5min').mean().reset_index()
    
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        subplot_titles=("Temperatura (°C)", "Humedad (%)")
    )
    
    for sensor in grouped_df['sensor'].unique():
        sensor_data = grouped_df[grouped_df['sensor'] == sensor]
        fig.add_trace(
            go.Scatter(
                x=sensor_data['timestamp'],
                y=sensor_data['t'],
                mode='lines',
                name=sensor,
                line_shape='spline'
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=sensor_data['timestamp'],
                y=sensor_data['h'],
                mode='lines',
                name=sensor,
                line_shape='spline',
                showlegend=False
            ),
            row=2, col=1
        )
    
    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=600,
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.2,
            xanchor='center',
            x=0.5
        ),
        margin=dict(l=20, r=20, t=30, b=30)
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='lightgrey', gridwidth=0.2)
    fig.update_yaxes(showgrid=True, gridcolor='lightgrey', gridwidth=0.2)
    
    return to_html(
        fig,
        include_plotlyjs=True,
        full_html=False,
        config={'staticPlot': True}
    )


def get_start_date(timeframe: str, end_date: datetime = None) -> datetime:
    """
    Obtiene la fecha de inicio basada en el intervalo de tiempo seleccionado.

    Parámetros:
    - `timeframe`: Intervalo de tiempo seleccionado.
    - `end_date`: Fecha de fin del rango de datos (opcional).

    Retorna:
    - datetime: Fecha de inicio calculada.
    """
    time_windows = {
        '5s': timedelta(minutes=5),
        '1min': timedelta(minutes=15),
        '30min': timedelta(hours=12),
        '1h': timedelta(hours=24),
        '4h': timedelta(days=4),
        '1d': timedelta(days=7)
    }
    window = time_windows.get(timeframe.lower(), timedelta(minutes=15))
    return end_date - window