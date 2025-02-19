import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path
from loguru import logger
import numpy as np
from plotly.offline import plot

# Get project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

METRICS_CFG = {
    't': {
        'steps': [18, 24, 40],
        'unit': '°C',
        'title': 'Temperatura',
        'color_bars_gradient': [
            'rgba(135, 206, 235, 0.8)',
            'rgba(144, 238, 144, 0.6)',
            'rgba(255, 99, 71, 0.8)',
        ],
        'brand_color': '#dc3545',  # Rojo
    },
    'h': {
        'steps': [40, 55, 100],
        'unit': '%HR',
        'title': 'Humedad',
        'color_bars_gradient': [
            'rgba(255, 198, 109, 0.8)',
            'rgba(152, 251, 152, 0.6)',
            'rgba(100, 149, 237, 0.8)',
        ],
        'brand_color': '#1f77b4',  # Azul
    },
    'l': {
        'steps': [0, 900, 1000],
        'unit': 'lum',
        'title': 'Luz',
        'color_bars_gradient': [
            'rgba(105, 105, 105, 0.2)',
            'rgba(255, 255, 153, 0.6)'
        ],
        'brand_color': '#ffc107',  # Amarillo
    },
    's': {
        'steps': [0, 30, 60, 100],
        'unit': '%H',
        'title': 'Sustrato',
        'color_bars_gradient': [
            'rgba(255, 198, 109, 0.8)',
            'rgba(152, 251, 152, 0.6)',
            'rgba(100, 149, 237, 0.8)',
        ],
        'brand_color': '#28a745',  # Verde
    }
}

def gauge_plot(value, metric, sensor, timestamp=None):
    metric_cfg = METRICS_CFG.get(metric)
    if not metric_cfg:
        return "<div>Invalid metric</div>"

    steps = metric_cfg['steps']

    # Título principal: Título de la métrica
    main_title = f"{metric_cfg['title']} en {metric_cfg['unit']}"

    # Subtítulo: Nombre del sensor (convertido a Title Case)
    sensor_name = str(sensor).title()

    fig = go.Figure()
    max_value = steps[-1]

    # Generate gauge steps depending on whether the first step is zero <- acá ganó o3-mini... para lo que va a durar: se va a models.py pronto...
    if steps[0] != 0:
        gauge_steps = (
            [{'range': [0, steps[0]], 'color': metric_cfg['color_bars_gradient'][0]}] +
            [{'range': [steps[i-1], steps[i]], 'color': metric_cfg['color_bars_gradient'][i]} for i in range(1, len(steps))]
        )
    else:
        gauge_steps = [
            {'range': [steps[i-1], steps[i]], 'color': metric_cfg['color_bars_gradient'][i-1]}
            for i in range(1, len(steps))
        ]
    # es más feo que ver chess cpu vs cpud

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0.15, 1]}, 
        number={
            'font': {'size': 24,
                     'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'},
            'suffix': f" {metric_cfg['unit']}",
            'valueformat': '.1f' if metric != 'l' else '.0f'
        },
        gauge={
            'axis': {
                'range': [0, max_value],
                'tickwidth': 1,
                'tickcolor': "#888888",
                'tickfont': {'size': 10,
                             'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'},
                'tickmode': 'linear',
                'dtick': max_value / 5
            },
            'bar': {'color': "rgba(150, 150, 150, 0.5)"},
            'bgcolor': "white",
            'borderwidth': 0,
            'steps': gauge_steps,
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.8,
                'value': value
            }
        }
    ))

    # Format the timestamp for display
    if timestamp:
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')
    else:
        timestamp_str = ""

    fig.update_layout(
        height=180,
        width=200,
        margin=dict(l=25, r=25, t=70, b=0),
        paper_bgcolor="white",
        font={'color': "#666666",
                 'family': "Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif"},
        showlegend=False,
        title={
            'text': f"<b>{main_title}</b><br><span style='font-size:0.8em;'>sensor {sensor_name}</span>",
            'y': 0.90,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {
                'size': 16,
                'color': '#5f9b62',
                'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'
            }
        },
        annotations=[
            dict(
                x=1,
                y=0,
                xref="paper",
                yref="paper",
                text=f"<span style='font-size:0.8em; color: #A9A9A9;'>último: {timestamp_str}</span>",
                showarrow=False,
                xanchor="right",
                yanchor="bottom"
            )
        ]
    )

    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        config={'staticPlot': True, 'displayModeBar': False}
    )

def sensor_plot(df, sensor, metric, timeframe, start_date, end_date):
    """
    Generates a line plot HTML string.

    Args:
        df (pd.DataFrame): The DataFrame containing the data.
        sensor (str): The name of the sensor.
        metric (str): The metric being plotted.
        timeframe (str): The timeframe for the data.
        start_date (datetime): The start date of the data.
        end_date (datetime): The end date of the data.

    Returns:
        str: The HTML string for the line plot.
        int: The number of data points used to generate the chart
    """

    try:
        if df.empty:
            logger.warning("DataFrame vacío")
            return f'<div>No hay datos para {sensor} - {metric}</div>', 0
        
        # Filter out None or NaN values
        df = df.dropna(subset=['value'])
        processed_values = df['value'].tolist()
        processed_timestamps = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()
            
        metric_cfg = METRICS_CFG.get(metric, {'brand_color': '#808080', 'title': metric.title()})
        
        fig = go.Figure()
        
        if "steps" in metric_cfg:
            steps = metric_cfg["steps"]
            colors = metric_cfg["color_bars_gradient"]
            shapes = []
            if steps[0] != 0:
                shapes.append({
                    "type": "rect",
                    "xref": "paper",
                    "yref": "y",
                    "x0": 0,
                    "x1": 1,
                    "y0": 0,
                    "y1": steps[0],
                    "fillcolor": colors[0] if len(colors) > 0 else 'rgba(200,200,200,0.2)',
                    "opacity": 0.07,
                    "line": {"width": 0},
                })
            for i in range(1, len(steps)):
                fillcolor = colors[i] if i < len(colors) else 'rgba(200,200,200,0.2)'
                shapes.append({
                    "type": "rect",
                    "xref": "paper",
                    "yref": "y",
                    "x0": 0,
                    "x1": 1,
                    "y0": steps[i-1],
                    "y1": steps[i],
                    "fillcolor": fillcolor,
                    "opacity": 0.07, 
                    "line": {"width": 0},
                })
            min_y = (0 + steps[0]) / 2
            if len(steps) > 1:
                max_y = steps[-1] * 1.05 
            else:
                max_y = steps[0] * 1.5 
            y_range = [min_y, max_y]
        else:
            shapes = []
            y_range = None
        
        fig.add_trace(
            go.Scatter(
                x=processed_timestamps,
                y=processed_values,
                mode='lines',
                name=metric_cfg['title'],
                line=dict(color=metric_cfg['brand_color']),
                hovertemplate='%{y:.1f}'
            )
        )
        
        fig.update_layout(
            paper_bgcolor='white',
            plot_bgcolor='white',
            shapes=shapes,
            showlegend=False,
            height=None,
            width=None,
            autosize=True,
            margin=dict(l=90, r=20, t=20, b=20), 
            xaxis={
                'type': 'date',  # Forzar línea de tiempo en x
                'fixedrange': True,
                'tickmode': 'auto',
                'showgrid': True,
                'gridcolor': 'lightgrey',
                'gridwidth': 0.5,
                'griddash': 'dot',
                'visible': True,
                'range': [start_date.isoformat(), end_date.isoformat()]  # Establece los límites de la línea de tiempo
            },
            yaxis={
                'fixedrange': True,
                'range': y_range,
                'tickmode': 'auto',
                'showgrid': True,
                'gridcolor': 'lightgrey',
                'gridwidth': 0.5,
                'griddash': 'dot',
                'visible': True,
                'side': 'right' 
            },
            hovermode='x unified',
            annotations=[
                {
                    "x": -0.1,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "text": f"<b>{metric_cfg['title']} en {metric_cfg['unit']}</b><br><span style='font-size:0.8em;'>sensor {sensor.upper()}</span>",
                    "showarrow": False,
                    "textangle": -90,
                    "xanchor": "left",
                    "yanchor": "middle",
                    "font": {
                        "size": 16,
                        "color": "#5f9b62",
                        "family": "Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif"
                    }
                }
            ]
        )
        
        return pio.to_html(
            fig,
            include_plotlyjs=False,
            full_html=False,
            config={'staticPlot': True, 'displayModeBar': False, 'responsive': True}
        ), len(processed_values)
        
    except Exception as e:
        logger.error(f"Error en lineplot_generator: {str(e)}")
        return f'<div>Error generando el gráfico: {str(e)}</div>', 0

def calculate_vpd(t, h):
    svp = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
    vp = svp * (h / 100)
    return svp - vp

def vpd_plot(data, temp_min=10, temp_max=40, hum_min=20, hum_max=80):
    import plotly.graph_objects as go
    import plotly.io as pio
    
    filtered_data = [
        (room, temp, hum)
        for room, temp, hum in data
        if temp_min <= temp <= temp_max and hum_min <= hum <= hum_max
    ]
    if not filtered_data:
        return '<div>Sin datos en el rango especificado</div>'

    # Bandas de VPD
    vpd_bands = [
        ("Muy Húmedo", 0, 0.4, "rgba(245, 230, 255, 0.2)"),
        ("Propagación", 0.4, 0.8, "rgba(195, 230, 215, 0.5)"),
        ("Vegetación", 0.8, 1.2, "rgba(255, 225, 180, 0.5)"),
        ("Flora", 1.2, 1.6, "rgba(255, 200, 150, 0.5)"),
        ("Muy Seco", 1.6, 10.0, "rgba(255, 100, 100, 0.025)")
    ]
    temperatures = np.linspace(temp_min, temp_max, 200)

    def calc_hum_from_vpd(t, vpd):
        svp = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
        h = 100 * (1 - vpd / svp) if svp > 0 else 100
        return max(hum_min, min(hum_max, h))

    fig = go.Figure()
    for band_name, vpd_min, vpd_max, color in vpd_bands:
        h_upper = [calc_hum_from_vpd(t, vpd_min) for t in temperatures]
        h_lower = [calc_hum_from_vpd(t, vpd_max) for t in temperatures]
        fig.add_trace(go.Scatter(
            x=h_upper, y=temperatures, mode='lines', line=dict(width=0),
            fillcolor=color, showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=h_lower, y=temperatures, mode='lines', line=dict(width=0),
            fill='tonexty', fillcolor=color, name=band_name,
            showlegend=not band_name.startswith("Muy")
        ))

    # Agregar puntos para cada sala
    for room_name, temp, hum in filtered_data:
        current_vpd = calculate_vpd(temp, hum)
        fig.add_trace(go.Scatter(
            y=[temp], x=[hum], mode='markers+text',
            marker=dict(size=10, color='black'),
            text=[f"{room_name} {current_vpd:.1f} kPa"],
            textposition='middle right', textfont=dict(size=11),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Temp: %{y:.1f}°C<br>"
                "Hum: %{x:.1f}%<br>"
                f"VPD: {current_vpd:.2f} kPa<extra></extra>"
            ),
            showlegend=False
        ))

    fig.update_layout(
        legend=dict(orientation='h', yanchor='top', y=-0.1, xanchor='center', x=0.5),
        xaxis=dict(
            title='Humedad Relativa (%HR)', range=[hum_max, hum_min], dtick=10,
            gridcolor='rgba(200, 200, 200, 0.2)', side='bottom', tickfont=dict(size=10)
        ),
        yaxis=dict(
            title='Temperatura (°C)', range=[temp_max, temp_min], dtick=5,
            gridcolor='rgba(200, 200, 200, 0.2)', side='right', tickfont=dict(size=10)
        ),
        plot_bgcolor='white', margin=dict(l=50, r=50, t=50, b=70), height=600
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={'staticPlot': True})

def calculate_vpd(temp_celsius, humidity):
    # Saturation Vapor Pressure (SVP) in kPa
    svp = 0.6108 * np.exp((17.27 * temp_celsius) / (temp_celsius + 237.3))
    
    # Actual Vapor Pressure (AVP) in kPa
    avp = svp * (humidity / 100)
    
    # Vapor Pressure Deficit (VPD) in kPa
    vpd = svp - avp
    
    return round(vpd, 2)

def vpd_plot(data):
    """
    Generates a Plotly bar chart for Vapor Pressure Deficit (VPD) by room.

    Args:
        data (list of tuples): A list where each tuple contains the room name,
                                average temperature, and average humidity.
                                Example: [('Living Room', 22.5, 55), ('Bedroom', 21.0, 60)]

    Returns:
        str: HTML representation of the Plotly chart.
    """
    rooms = [item[0] for item in data]
    avg_temps = [item[1] for item in data]
    avg_humids = [item[2] for item in data]
    vpds = [calculate_vpd(temp, humid) for temp, humid in zip(avg_temps, avg_humids)]

    fig = go.Figure(data=[go.Bar(x=rooms, y=vpds,
                                 marker_color='skyblue')])

    fig.update_layout(title='Vapor Pressure Deficit (VPD) by Room',
                      xaxis_title='Room',
                      yaxis_title='VPD (kPa)',
                      template='plotly_white')

    plot_div = plot(fig, output_type='div', include_plotlyjs=False)
    return plot_div

