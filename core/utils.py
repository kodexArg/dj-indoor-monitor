from typing import List, Tuple
from django.conf import settings

# Python
from datetime import datetime, timedelta, timezone
import pytz

# Third-party
import pandas as pd
import plotly.graph_objs as go
from plotly.io import to_html
from plotly.subplots import make_subplots

def generate_plotly_chart(data: List[dict], metric: str, start_date: datetime, end_date: datetime, selected_timeframe: str, div_id: str = 'chart') -> Tuple[str, int]:
    """
    Genera HTML con gráfico estático Plotly.

    Parámetros:
    - `data`: Lista de diccionarios con los datos del sensor.
    - `metric`: Métrica a graficar (ej: 't' para temperatura).
    - `start_date`: Fecha de inicio del rango de datos.
    - `end_date`: Fecha de fin del rango de datos.
    - `selected_timeframe`: Intervalo de tiempo seleccionado.
    - `div_id`: ID del div donde se insertará el gráfico.

    Retorna:
    - tuple: (chart_html, plotted_points)
    """
    if not data:
        return f'<div id="{div_id}">No hay datos para mostrar</div>', 0
    
    plotted_points = 0  # Contador de puntos graficados
    
    # Crear DataFrame y asegurar que timestamp sea datetime64[ns, UTC]
    df = pd.DataFrame(data)
    
    # Convertir a timezone local después de asegurar que es UTC
    local_tz = pytz.timezone(settings.TIME_ZONE)
    start_date = start_date.astimezone(local_tz)
    end_date = end_date.astimezone(local_tz)
    
    # Adaptar dataframe
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)

    # Para 5s y 1min no agrupamos los datos
    if selected_timeframe.lower() in ['5s', '1min']:
        df = df.set_index('timestamp')
        fig = go.Figure()
        for sensor in df.groupby('sensor').groups.keys():
            sensor_data = df[df['sensor'] == sensor]
            plotted_points += len(sensor_data)  # Contar puntos sin agrupar
            if selected_timeframe.lower() == '5s':
                mode = 'lines+markers'
                marker = dict(size=6, symbol='circle')
            else:
                mode = 'lines'
                marker = dict()
                
            fig.add_trace(go.Scatter(
                x=sensor_data.index,
                y=sensor_data[metric],
                mode=mode,
                line_shape='spline',
                name=sensor,
                marker=marker
            ))
    elif selected_timeframe.lower() == '1d':
        df = df.set_index('timestamp')
        fig = go.Figure()
        
        for sensor in df.groupby('sensor').groups.keys():
            sensor_data = df[df['sensor'] == sensor]
            
            # Calcular OHLC (Open, High, Low, Close)
            daily_data = {
                'open': sensor_data[metric].iloc[-1],  # Primer valor del día
                'high': sensor_data[metric].max(),     # Máximo del día
                'low': sensor_data[metric].min(),      # Mínimo del día
                'close': sensor_data[metric].iloc[0]   # Último valor del día
            }
            
            # Determinar si es alcista o bajista
            is_bullish = daily_data['close'] >= daily_data['open']
            fill_color = 'white' if is_bullish else 'lightgray'
            
            # Añadir la vela
            fig.add_trace(go.Candlestick(
                x=[sensor_data.index[0]],  # Un solo punto temporal
                open=[daily_data['open']],
                high=[daily_data['high']],
                low=[daily_data['low']],
                close=[daily_data['close']],
                name=sensor,
                increasing=dict(line=dict(color='blue'), fillcolor='white'),
                decreasing=dict(line=dict(color='blue'), fillcolor='lightgray'),
                showlegend=True
            ))
            
    else:
        # agrupar df por timestamp según la freq
        timeframe_seconds = {
            '30min': 300,
            '1h': 600,
            '4h': 1200,
            '1d': 600 
        }
        
        seconds = timeframe_seconds.get(selected_timeframe.lower(), 5)
        resample_rule = f'{seconds}s'

        df = df.set_index('timestamp')
        grouped_df = df.groupby('sensor').resample(resample_rule).agg({
            metric: 'mean'
        })

        # Filtrar valores <= 1 después de la agrupación
        grouped_df = grouped_df[grouped_df[metric] > 1]

        fig = go.Figure()
        
        for sensor in grouped_df.index.get_level_values('sensor').unique():
            sensor_data = grouped_df.loc[sensor]
            plotted_points += len(sensor_data)
            
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
    ), plotted_points



def generate_dual_plotly_chart(data: List[dict], start_date: datetime, end_date: datetime) -> str:
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
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    
    # Agrupar datos cada 5 minutos
    df = df.set_index('timestamp')
    grouped_df = df.groupby('sensor').resample('5min').mean().reset_index()
    
    # Crear subplots
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        subplot_titles=("Temperatura (°C)", "Humedad (%)")
    )
    
    # Agregar trazas de temperatura y humedad
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
                showlegend=False  # Oculta la leyenda duplicada
            ),
            row=2, col=1
        )
    
    # Configurar diseño
    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=600,  # Ajustar altura
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


def generate_simple_plotly_chart(data: List[dict], metric: str, start_date: datetime, end_date: datetime) -> str:
    """
    Genera un gráfico Plotly simplificado para dispositivos antiguos.

    Parámetros:
    - `data`: Lista de diccionarios con los datos del sensor.
    - `metric`: Métrica a graficar (ej: 't' para temperatura).
    - `start_date`: Fecha de inicio del rango de datos.
    - `end_date`: Fecha de fin del rango de datos.

    Retorna:
    - str: HTML del gráfico generado.
    """
    if not data:
        return '<div>No hay datos para mostrar</div>'
    
    # Crear DataFrame y configurar timezone
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    
    # Agrupar datos cada 5 minutos
    df = df.set_index('timestamp')
    grouped_df = df.groupby('sensor').resample('5min').agg({
        metric: 'mean'
    })
    
    # Filtrar valores <= 1 después de la agrupación
    grouped_df = grouped_df[grouped_df[metric] > 1]
    
    # Crear gráfico
    fig = go.Figure()
    
    for sensor in grouped_df.index.get_level_values('sensor').unique():
        sensor_data = grouped_df.loc[sensor]
        fig.add_trace(go.Scatter(
            x=sensor_data.index,
            y=sensor_data[metric],
            mode='lines',
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
        margin=dict(l=20, r=20, t=30, b=30),
        yaxis=dict(
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot'
        ),
        xaxis=dict(
            gridcolor='lightgrey',
            gridwidth=0.2,
            griddash='dot'
        ),
    )
    
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
