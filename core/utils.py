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


def get_timedelta_from_timeframe(timeframe: str) -> timedelta:
    """
    Convierte un timeframe en su timedelta correspondiente.
    Para ser usado con timeframes válidos ('5s', '5T', '30T', '1h', '4h', '1D').

    Retorna:
    - timedelta: Ventana de tiempo correspondiente al timeframe
    """
    time_windows = {
        '5s': timedelta(minutes=5),
        '1T': timedelta(minutes=15),
        '30T': timedelta(hours=12),
        '1h': timedelta(hours=24),
        '4h': timedelta(days=4),
        '1D': timedelta(days=7)
    }
    return time_windows[timeframe]


def get_start_date(timeframe: str, end_date: datetime = None) -> datetime:
    """
    Calcula la fecha de inicio (usada 'por defecto') basada en el intervalo de tiempo seleccionado.

    Parámetros:
    - `timeframe`: Intervalo de tiempo seleccionado.
    - `end_date`: Fecha de fin del rango de datos (opcional).

    Retorna:
    - datetime: Fecha de inicio calculada.
    """
    window = get_timedelta_from_timeframe(timeframe)
    return end_date - window


def format_timestamp(timestamp: datetime, include_seconds: bool = False) -> str:
    """
    Formatea un timestamp para visualización amigable.
    
    Args:
        timestamp: Datetime a formatear
        include_seconds: Si True, incluye los segundos en el formato
    
    Returns:
        String formateado, ejemplo: "26 Ene 15:30" o "26 Ene 15:30:45"
    """
    if timestamp is None:
        return "N/A"
        
    # Convertir a timezone local si tiene timezone
    if timestamp.tzinfo is not None:
        local_tz = pytz.timezone(settings.TIME_ZONE)
        timestamp = timestamp.astimezone(local_tz)
    
    # Diccionario de meses en español
    meses = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    # Formato base
    fecha = f"{timestamp.day} {meses[timestamp.month]}"
    hora = f"{timestamp.hour:02d}:{timestamp.minute:02d}"
    
    if include_seconds:
        hora += f":{timestamp.second:02d}"
    
    return f"{fecha} {hora}"