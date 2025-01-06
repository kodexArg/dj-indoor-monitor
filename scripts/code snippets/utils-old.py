from typing import List, Tuple
from django.conf import settings
from datetime import datetime, timedelta, timezone
import pytz
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
    
    plotted_points = 0
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    start_date = start_date.astimezone(local_tz)
    end_date = end_date.astimezone(local_tz)
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)

    if selected_timeframe.lower() in ['5s', '1min']:
        df = df.set_index('timestamp')
        fig = go.Figure()
        for sensor in df.groupby('sensor').groups.keys():
            sensor_data = df[df['sensor'] == sensor]
            plotted_points += len(sensor_data)
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
            
            daily_data = {
                'open': sensor_data[metric].iloc[-1],
                'high': sensor_data[metric].max(),
                'low': sensor_data[metric].min(),
                'close': sensor_data[metric].iloc[0]
            }
            
            is_bullish = daily_data['close'] >= daily_data['open']
            fill_color = 'white' if is_bullish else 'lightgray'
            
            fig.add_trace(go.Candlestick(
                x=[sensor_data.index[0]],
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
        include_plotlyjs=False, 
        full_html=False,
        div_id=div_id,
        config={'displayModeBar': False}
    ), plotted_points





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
    
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    
    df = df.set_index('timestamp')
    grouped_df = df.groupby('sensor').resample('5min').agg({
        metric: 'mean'
    })
    
    grouped_df = grouped_df[grouped_df[metric] > 1]
    
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




def generate_gauges(data: List[dict], end_date: datetime) -> str:
    """
    Genera HTML con medidores gauge para cada sensor y métrica.

    Parámetros:
    - `data`: Lista de diccionarios con los últimos datos de los sensores.
    - `end_date`: Fecha de fin del rango de datos.

    Retorna:
    - str: HTML del gráfico generado.
    """
    if not data:
        return '<div id="gauges-container">No hay datos para mostrar</div>'
    
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    df = df.sort_values('timestamp').groupby('sensor').last()
    
    fig = make_subplots(
        rows=len(df), cols=2,
        specs=[[{'type': 'indicator'}, {'type': 'indicator'}] for _ in range(len(df))],
        vertical_spacing=0.5,
        horizontal_spacing=0.15,
        subplot_titles=[''] * (2 * len(df))
    )
    
    for idx, (sensor, row) in enumerate(df.iterrows(), 1):
        # Temperature gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=row['t'],
                title={
                    'text': f'<b>{sensor}</b>',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                number={
                    'font': {'size': 24, 'color': '#92c594'},  # brand-green
                    'suffix': '°C',
                    'prefix': '<br>',
                    'valueformat': '.1f'
                },
                gauge={
                    'shape': "angular",
                    'axis': {
                        'range': [0, 50],  # Rango completo 0-50°C
                        'tickwidth': 1,
                        'tickcolor': "#92c594",  # brand-green
                        'ticklen': 3,
                        'tickmode': 'array',
                        'tickvals': [0, 15, 30, 45, 50],
                        'ticktext': ['0°', '15°', '30°', '45°', '50°'],
                        'tickfont': {'size': 12}
                    },
                    'bar': {'color': "#92c594", 'thickness': 0.5},  # brand-green
                    'bgcolor': "white",
                    'borderwidth': 1,
                    'bordercolor': "#92c594",  # brand-green
                    'steps': [
                        {'range': [0, 18], 'color': '#e5e5e5'},  # brand-gray-light
                        {'range': [18, 30], 'color': '#fff'}, 
                        {'range': [30, 45], 'color': '#e5e5e5'},   # brand-gray-light
                        {'range': [45, 50], 'color': '#ff0000'}   # red
                    ]
                }
            ),
            row=idx, col=1
        )
        
        # Humidity gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=row['h'],
                title={
                    'text': f'<b>{sensor}</b>',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                number={
                    'font': {'size': 24, 'color': '#92c594'},  # brand-green
                    'suffix': '%',
                    'prefix': '<br>',
                    'valueformat': '.1f'
                },
                gauge={
                    'shape': "angular",
                    'axis': {
                        'range': [0, 100],  # Rango completo 0-100%
                        'tickwidth': 1,
                        'tickcolor': "#92c594",  # brand-green
                        'ticklen': 3,
                        'tickmode': 'array',
                        'tickvals': [0, 30, 55, 80, 100],
                        'ticktext': ['0%', '30%', '55%', '80%', '100%'],
                        'tickfont': {'size': 12}
                    },
                    'bar': {'color': "#92c594", 'thickness': 0.2},  # brand-green
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "#92c594",  # brand-green
                    'steps': [
                        {'range': [0, 30], 'color': '#e5e5e5'},  # brand-gray-light
                        {'range': [30, 40], 'color': '#e5e5e5'},  # brand-gray-light
                        {'range': [40, 70], 'color': '#d4edda'},  # brand-green-light
                        {'range': [70, 80], 'color': '#e5e5e5'},   # brand-gray-light
                        {'range': [80, 100], 'color': '#ff0000'}   # red
                    ]
                }
            ),
            row=idx, col=2
        )
    
    fig.update_layout(
        height=250 * len(df),
        margin=dict(t=50, b=30, l=30, r=30),
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='white',
        grid={'rows': len(df), 'columns': 2, 'pattern': 'independent'},
        font={'family': "Arial, sans-serif"}
    )
    
    return to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        div_id='gauges-container',
        config={'displayModeBar': False}
    )

def generate_gauge(data: List[dict], end_date: datetime, sensor_name: str, metric: str) -> str:
    """
    Genera HTML con un único medidor gauge minimalista.

    Parámetros:
    - `data`: Lista de diccionarios con los datos del sensor.
    - `end_date`: Fecha de fin del rango de datos.
    - `sensor_name`: Nombre del sensor a mostrar.
    - `metric`: Métrica a mostrar ('t' o 'h').

    Retorna:
    - str: HTML del gauge generado.
    """
    if not data:
        return '<div>No hay datos para mostrar</div>'
    
    metric_config = {
        't': {
            'suffix': '°C',
            'range': [15, 35],
            'steps': [
                {'range': [15, 18], 'color': 'rgba(255, 0, 0, 0.08)'},
                {'range': [18, 30], 'color': 'rgba(0, 255, 0, 0.08)'},
                {'range': [30, 35], 'color': 'rgba(255, 0, 0, 0.08)'}
            ],
            'subtitle': 'Temperatura'
        },
        'h': {
            'suffix': '%',
            'range': [30, 80],
            'steps': [
                {'range': [30, 40], 'color': 'rgba(255, 0, 0, 0.08)'},
                {'range': [40, 70], 'color': 'rgba(0, 255, 0, 0.08)'},
                {'range': [70, 80], 'color': 'rgba(255, 0, 0, 0.08)'}
            ],
            'subtitle': 'Humedad'
        }
    }
    
    df = pd.DataFrame(data)
    df = df[df['sensor'] == sensor_name]
    if df.empty:
        return f'<div>No hay datos para el sensor {sensor_name}</div>'
    
    latest = df.sort_values('timestamp').iloc[-1][metric]
    
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=latest,
            title={
                'text': f'<b>{sensor_name}</b><br><span style="font-size:0.8em">{metric_config[metric]["subtitle"]}</span>',
                'font': {'size': 24, 'family': 'Arial Black'}
            },
            number={
                'font': {'size': 36, 'color': 'darkblue'},
                'suffix': metric_config[metric]['suffix']
            },
            gauge={
                'shape': "angular",
                'axis': {
                    'range': metric_config[metric]['range'],
                    'visible': False,
                    'tickwidth': 0
                },
                'bar': {'color': "darkblue", 'thickness': 0.15},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "darkblue",
                'steps': metric_config[metric]['steps']
            }
        )
    )
    
    fig.update_layout(
        height=300,
        margin=dict(t=25, b=15, l=25, r=25),
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font={'family': "Arial, sans-serif"}
    )
    
    return to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        config={'displayModeBar': False}
    )

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
    
    plotted_points = 0
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    start_date = start_date.astimezone(local_tz)
    end_date = end_date.astimezone(local_tz)
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)

    if selected_timeframe.lower() in ['5s', '1min']:
        df = df.set_index('timestamp')
        fig = go.Figure()
        for sensor in df.groupby('sensor').groups.keys():
            sensor_data = df[df['sensor'] == sensor]
            plotted_points += len(sensor_data)
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
            
            daily_data = {
                'open': sensor_data[metric].iloc[-1],
                'high': sensor_data[metric].max(),
                'low': sensor_data[metric].min(),
                'close': sensor_data[metric].iloc[0]
            }
            
            is_bullish = daily_data['close'] >= daily_data['open']
            fill_color = 'white' if is_bullish else 'lightgray'
            
            fig.add_trace(go.Candlestick(
                x=[sensor_data.index[0]],
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
        include_plotlyjs=False, 
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
    
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    
    df = df.set_index('timestamp')
    grouped_df = df.groupby('sensor').resample('5min').agg({
        metric: 'mean'
    })
    
    grouped_df = grouped_df[grouped_df[metric] > 1]
    
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

def generate_gauges(data: List[dict], end_date: datetime) -> str:
    """
    Genera HTML con medidores gauge para cada sensor y métrica.

    Parámetros:
    - `data`: Lista de diccionarios con los últimos datos de los sensores.
    - `end_date`: Fecha de fin del rango de datos.

    Retorna:
    - str: HTML del gráfico generado.
    """
    if not data:
        return '<div id="gauges-container">No hay datos para mostrar</div>'
    
    df = pd.DataFrame(data)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    df = df.sort_values('timestamp').groupby('sensor').last()
    
    fig = make_subplots(
        rows=len(df), cols=2,
        specs=[[{'type': 'indicator'}, {'type': 'indicator'}] for _ in range(len(df))],
        vertical_spacing=0.5,
        horizontal_spacing=0.15,
        subplot_titles=[''] * (2 * len(df))
    )
    
    for idx, (sensor, row) in enumerate(df.iterrows(), 1):
        # Temperature gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=row['t'],
                title={
                    'text': f'<b>{sensor}</b>',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                number={
                    'font': {'size': 24, 'color': '#92c594'},  # brand-green
                    'suffix': '°C',
                    'prefix': '<br>',
                    'valueformat': '.1f'
                },
                gauge={
                    'shape': "angular",
                    'axis': {
                        'range': [0, 50],  # Rango completo 0-50°C
                        'tickwidth': 1,
                        'tickcolor': "#92c594",  # brand-green
                        'ticklen': 3,
                        'tickmode': 'array',
                        'tickvals': [0, 15, 30, 45, 50],
                        'ticktext': ['0°', '15°', '30°', '45°', '50°'],
                        'tickfont': {'size': 12}
                    },
                    'bar': {'color': "#92c594", 'thickness': 0.5},  # brand-green
                    'bgcolor': "white",
                    'borderwidth': 1,
                    'bordercolor': "#92c594",  # brand-green
                    'steps': [
                        {'range': [0, 18], 'color': '#e5e5e5'},  # brand-gray-light
                        {'range': [18, 30], 'color': '#fff'}, 
                        {'range': [30, 45], 'color': '#e5e5e5'},   # brand-gray-light
                        {'range': [45, 50], 'color': '#ff0000'}   # red
                    ]
                }
            ),
            row=idx, col=1
        )
        
        # Humidity gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=row['h'],
                title={
                    'text': f'<b>{sensor}</b>',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                number={
                    'font': {'size': 24, 'color': '#92c594'},  # brand-green
                    'suffix': '%',
                    'prefix': '<br>',
                    'valueformat': '.1f'
                },
                gauge={
                    'shape': "angular",
                    'axis': {
                        'range': [0, 100],  # Rango completo 0-100%
                        'tickwidth': 1,
                        'tickcolor': "#92c594",  # brand-green
                        'ticklen': 3,
                        'tickmode': 'array',
                        'tickvals': [0, 30, 55, 80, 100],
                        'ticktext': ['0%', '30%', '55%', '80%', '100%'],
                        'tickfont': {'size': 12}
                    },
                    'bar': {'color': "#92c594", 'thickness': 0.2},  # brand-green
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "#92c594",  # brand-green
                    'steps': [
                        {'range': [0, 30], 'color': '#e5e5e5'},  # brand-gray-light
                        {'range': [30, 40], 'color': '#e5e5e5'},  # brand-gray-light
                        {'range': [40, 70], 'color': '#d4edda'},  # brand-green-light
                        {'range': [70, 80], 'color': '#e5e5e5'},   # brand-gray-light
                        {'range': [80, 100], 'color': '#ff0000'}   # red
                    ]
                }
            ),
            row=idx, col=2
        )
    
    fig.update_layout(
        height=250 * len(df),
        margin=dict(t=50, b=30, l=30, r=30),
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='white',
        grid={'rows': len(df), 'columns': 2, 'pattern': 'independent'},
        font={'family': "Arial, sans-serif"}
    )
    
    return to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        div_id='gauges-container',
        config={'displayModeBar': False}
    )

def generate_gauge(data: List[dict], end_date: datetime, sensor_name: str, metric: str) -> str:
    """
    Genera HTML con un único medidor gauge minimalista.

    Parámetros:
    - `data`: Lista de diccionarios con los datos del sensor.
    - `end_date`: Fecha de fin del rango de datos.
    - `sensor_name`: Nombre del sensor a mostrar.
    - `metric`: Métrica a mostrar ('t' o 'h').

    Retorna:
    - str: HTML del gauge generado.
    """
    if not data:
        return '<div>No hay datos para mostrar</div>'
    
    metric_config = {
        't': {
            'suffix': '°C',
            'range': [15, 35],
            'steps': [
                {'range': [15, 18], 'color': 'rgba(255, 0, 0, 0.08)'},
                {'range': [18, 30], 'color': 'rgba(0, 255, 0, 0.08)'},
                {'range': [30, 35], 'color': 'rgba(255, 0, 0, 0.08)'}
            ],
            'subtitle': 'Temperatura'
        },
        'h': {
            'suffix': '%',
            'range': [30, 80],
            'steps': [
                {'range': [30, 40], 'color': 'rgba(255, 0, 0, 0.08)'},
                {'range': [40, 70], 'color': 'rgba(0, 255, 0, 0.08)'},
                {'range': [70, 80], 'color': 'rgba(255, 0, 0, 0.08)'}
            ],
            'subtitle': 'Humedad'
        }
    }
    
    df = pd.DataFrame(data)
    df = df[df['sensor'] == sensor_name]
    if df.empty:
        return f'<div>No hay datos para el sensor {sensor_name}</div>'
    
    latest = df.sort_values('timestamp').iloc[-1][metric]
    
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=latest,
            title={
                'text': f'<b>{sensor_name}</b><br><span style="font-size:0.8em">{metric_config[metric]["subtitle"]}</span>',
                'font': {'size': 24, 'family': 'Arial Black'}
            },
            number={
                'font': {'size': 36, 'color': 'darkblue'},
                'suffix': metric_config[metric]['suffix']
            },
            gauge={
                'shape': "angular",
                'axis': {
                    'range': metric_config[metric]['range'],
                    'visible': False,
                    'tickwidth': 0
                },
                'bar': {'color': "darkblue", 'thickness': 0.15},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "darkblue",
                'steps': metric_config[metric]['steps']
            }
        )
    )
    
    fig.update_layout(
        height=300,
        margin=dict(t=25, b=15, l=25, r=25),
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font={'family': "Arial, sans-serif"}
    )
    
    return to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        config={'displayModeBar': False}
    )
