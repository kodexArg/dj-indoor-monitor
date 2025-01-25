# Python built-in
from typing import List, Tuple
from datetime import datetime, timedelta, timezone
import numpy as np

# Django
from django.conf import settings

# Third party
from loguru import logger
import pytz
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
import plotly.subplots as make_subplots

TIMEFRAME_MAP = {
    # API/UI format : Pandas format
    '5S': '5S',
    '1T': '1min',
    '30T': '30min',
    '1H': '1h', 
    '4H': '4h',
    '1D': '1D'
}

# Configure logger
logger.configure(
    handlers=[
        {
            "sink": lambda msg: print(msg),
            "format": "<level>{level: <8}</level> | <level>{message}</level>",
            "level": "DEBUG",  # Changed from INFO to DEBUG for console
            "backtrace": True,
            "diagnose": True
        }
    ]
)


def overview_plot_generator(data, metric, start_date, end_date, selected_timeframe, div_id='chart'):
    """
    Genera HTML con gráfico estático Plotly usando datos pre-agrupados.

    Parámetros:
    - `data`: Lista de diccionarios con la estructura timeframed:
        {
            'timestamp': '2024-01-01T00:00:00Z',
            'sensor': 'sensor-id',
            'temperature': {'mean': 20.5, ...},
            'humidity': {'mean': 65.2, ...}
        }
    - `metric`: Métrica a graficar ('t' para temperatura, 'h' para humedad).
    - `start_date`: Fecha de inicio del rango de datos.
    - `end_date`: Fecha de fin del rango de datos.
    - `selected_timeframe`: Intervalo de tiempo seleccionado.
    - `div_id`: ID del div donde se insertará el gráfico.

    Retorna:
    - tuple: (chart_html, plotted_points)
    """
    if not data:
        return f'<div id="{div_id}">No hay datos para mostrar</div>', 0
    
    # Convertir a timezone local
    local_tz = pytz.timezone(settings.TIME_ZONE)
    start_date = start_date.astimezone(local_tz)
    end_date = end_date.astimezone(local_tz)

    # Inicializar figura
    fig = go.Figure()
    plotted_points = 0

    # Agrupar datos por sensor
    sensors = {}
    for item in data:
        sensor = item['sensor']
        if sensor not in sensors:
            sensors[sensor] = {'x': [], 'y': []}
        
        # Convertir timestamp a zona horaria local
        timestamp = pd.to_datetime(item['timestamp']).tz_convert(local_tz)
        sensors[sensor]['x'].append(timestamp)
        
        # Obtener el valor según la métrica
        value = item['temperature']['mean'] if metric == 't' else item['humidity']['mean']
        sensors[sensor]['y'].append(value)
        plotted_points += 1

    # Crear trazas para cada sensor
    for sensor, sensor_data in sensors.items():
        fig.add_trace(go.Scatter(
            x=sensor_data['x'],
            y=sensor_data['y'],
            mode='lines',  # Siempre usar líneas, sin importar el timeframe
            name=sensor,
            line_shape='spline'
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
        margin=dict(l=20, r=20, t=5, b=20),
        yaxis=dict(
            range=[min(sum([d['y'] for d in sensors.values()], [])) - 2,
                  max(sum([d['y'] for d in sensors.values()], [])) + 2],
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot'
        ),
        xaxis=dict(
            range=[start_date, end_date],
            showgrid=True,
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot',
            fixedrange=True
        ),
        hovermode='x unified'
    )

    # Logging
    if sensors:
        oldest_timestamp = min(min(s['x']) for s in sensors.values())
        logger.debug(
            f"Fecha de inicio solicitada: {format_timestamp(start_date)}, "
            f"Fecha del registro más antiguo: {format_timestamp(oldest_timestamp)}, "
            f"Cantidad de registros: {plotted_points}"
        )

    html_chart = pio.to_html(
        fig,
        include_plotlyjs=True,
        full_html=False,
        div_id=div_id,
        config={'displayModeBar': False}
    )

    return html_chart, plotted_points

def old_devices_plot_generator(data, start_date, end_date):
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
        height=400,
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
    
    return pio.to_html(
        fig,
        include_plotlyjs=True,
        full_html=False,
        config={'staticPlot': True}
    )


def sensor_plot_generator(data, sensor, start_date, end_date, selected_timeframe, div_id='chart'):
    filtered_data = [item for item in data if item['sensor'] == sensor]
    if not filtered_data:
        return f'<div id="{div_id}">No hay datos para {sensor}</div>', 0

    local_tz = pytz.timezone(settings.TIME_ZONE)
    start_date = start_date.astimezone(local_tz)
    end_date = end_date.astimezone(local_tz)

    fig = go.Figure()
    x_vals = []
    temp_vals = []
    hum_vals = []
    for item in filtered_data:
        ts = pd.to_datetime(item['timestamp']).tz_convert(local_tz)
        x_vals.append(ts)
        temp_vals.append(item['temperature']['mean'])
        hum_vals.append(item['humidity']['mean'])

    mode = 'lines' if selected_timeframe.lower() != '5s' else 'lines+markers'
    
    # Humedad en eje Y primario (izquierda)
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=hum_vals,
            mode=mode,
            name='Humedad',
            line_shape='spline',
            line=dict(color='#1f77b4'),  # Azul
            yaxis='y'
        )
    )
    
    # Temperatura en eje Y secundario (derecha)
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=temp_vals,
            mode=mode,
            name='Temperatura',
            line_shape='spline',
            line=dict(color='#dc3545'),  # Rojo
            yaxis='y2'
        )
    )

    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=False,  # Cambiado de True a False
        title=dict(
            text=f'Sensor {sensor}',
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top',
            font=dict(size=14)
        ),
        margin=dict(l=50, r=50, t=30, b=50),
        xaxis=dict(
            range=[start_date, end_date],
            fixedrange=True,
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot'
        ),
        yaxis=dict(
            title=dict(
                text="Humedad en %",
                standoff=0,
                font=dict(size=10)
            ),
            range=[0, 100],
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot',
            titlefont=dict(color="#1f77b4"),  # Azul
            tickfont=dict(color="#1f77b4")    # Azul
        ),
        yaxis2=dict(
            title=dict(
                text="Temperatura en °C",
                standoff=0,
                font=dict(size=10)
            ),
            range=[0, 100],
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot',
            overlaying='y',
            side='right',
            titlefont=dict(color="#dc3545"),  # Rojo
            tickfont=dict(color="#dc3545")    # Rojo
        ),
        hovermode='x unified'
    )

    html_chart = pio.to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        div_id=div_id,
        config={'staticPlot': True}
    )
    return html_chart, len(filtered_data)


def get_timedelta_from_timeframe(timeframe):
    """
    Convierte un timeframe en su timedelta correspondiente.
    """
    time_windows = {
        '5S': timedelta(minutes=15),  # Ventana más corta para datos de 5 segundos
        '1T': timedelta(hours=3),
        '30T': timedelta(hours=36),
        '1H': timedelta(days=3),
        '4H': timedelta(days=12),
        '1D': timedelta(days=42)
    }
    return time_windows[timeframe.upper()]


def get_start_date(timeframe, end_date=None):
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


def format_timestamp(timestamp, include_seconds=False):
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


# VPD
def calculate_vpd(t, h):
    svp = 0.6108 * np.exp((17.27 * t) / (t + 237.3))  # Presión de vapor de saturación
    vp = svp * (h / 100)  # Presión de vapor actual
    vpd = svp - vp  # Déficit de presión de vapor
    return vpd

def vpd_chart_generator(data):
    """
    Genera un gráfico de VPD optimizado para cultivo de cannabis con ejes invertidos.
    """
    temperatures = np.linspace(10, 40, 200)
    
    vpd_bands = [
        ("Too Humid", 0, 0.4, "rgba(245, 230, 255, 0.2)"),
        ("Propagación", 0.4, 0.8, "rgba(195, 230, 215, 0.5)"),
        ("Vegetación", 0.8, 1.2, "rgba(255, 225, 180, 0.5)"),
        ("Veg. Tardía / Flora", 1.2, 1.6, "rgba(255, 200, 150, 0.5)"),
        ("Too Dry", 1.6, 10.0, "rgba(255, 100, 100, 0.025)")
    ]

    fig = go.Figure()

    def calculate_h(t, vpd):
        svp = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
        h = 100 * (1 - vpd / svp) if svp > 0 else 100
        return max(0, min(100, h))

    for band_name, vpd_min, vpd_max, color in vpd_bands:
        h_upper = [calculate_h(t, vpd_min) for t in temperatures]
        h_lower = [calculate_h(t, vpd_max) for t in temperatures]
        
        fig.add_trace(go.Scatter(
            x=h_upper,
            y=temperatures,
            mode='lines',
            line=dict(width=0),
            fillcolor=color,
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=h_lower,
            y=temperatures,
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor=color,
            name=band_name,
            showlegend=not band_name.startswith("Too")
        ))

    # Agregar puntos y etiquetas directamente
    for sensor_id, temperature, humidity in data:
        current_vpd = calculate_vpd(temperature, humidity)
        
        # Agregar líneas punteadas
        fig.add_trace(go.Scatter(
            x=[0, humidity],
            y=[temperature, temperature],
            mode='lines',
            line=dict(color='rgba(0,0,0,0.1)', dash='dot'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=[humidity, humidity],
            y=[40, temperature],
            mode='lines',
            line=dict(color='rgba(0,0,0,0.1)', dash='dot'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Agregar punto y etiqueta
        fig.add_trace(go.Scatter(
            y=[temperature],
            x=[humidity],
            mode='markers+text',
            marker=dict(size=10, color='black'),
            text=[f"{sensor_id} {current_vpd:.1f}kPa"],
            textposition='middle right',
            textfont=dict(size=10),
            hovertemplate=(
                '<b>%{text}</b><br>'
                'Temperatura: %{y:.1f}°C<br>'
                'Humedad: %{x:.1f}%<br>'
                f'VPD: {current_vpd:.2f} kPa<extra></extra>'
            ),
            showlegend=False
        ))

    fig.update_layout(
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.1,
            xanchor='center',
            x=0.5
        ),
        xaxis=dict(
            title='Humedad Relativa (%HR)',
            range=[100, 0],  # Eje invertido
            dtick=10,
            gridcolor='rgba(200, 200, 200, 0.2)',
            side='bottom'
        ),
        yaxis=dict(
            title='Temperatura (°C)',
            range=[40, 10],
            dtick=5,
            gridcolor='rgba(200, 200, 200, 0.2)',
            autorange='reversed',
            side='right',
            title_standoff=0
        ),
        plot_bgcolor='white',
        margin=dict(l=50, r=50, t=50, b=50),
        height=600
    )

    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={'staticPlot': True})