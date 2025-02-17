import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path
from loguru import logger

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

def gauge_generator(value, metric, sensor):
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

    fig.update_layout(
        height=180,
        width=200,
        margin=dict(l=20, r=20, t=80, b=0),
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

