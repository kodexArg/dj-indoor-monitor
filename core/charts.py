import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import pytz
from django.conf import settings

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
        'unit': '%',
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
        'unit': '%',
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
    main_title = metric_cfg['title']

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

def lineplot_generator(values, sensor, metric, start_date, end_date):
    if not values:
        return f'<div>No hay datos para {sensor} - {metric}</div>', 0
    x_vals = [x for x, y in values]
    y_vals = [y for x, y in values]
    metric_cfg = METRICS_CFG.get(metric, {'brand_color': '#808080', 'title': metric.title()})
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines',
            name=metric_cfg['title'],
            line=dict(color=metric_cfg['brand_color'])
        )
    )
    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=False,
        height=180,
        width=540,
        margin=dict(l=20, r=20, t=80, b=0),
        title={
            'text': f"<b>{metric_cfg['title']}</b><br><span style='font-size:0.8em;'>sensor {sensor.title()}</span>",
            'y': 0.90,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 16, 'color': '#5f9b62', 'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'}
        },
        xaxis={
            'range': [start_date, end_date],
            'fixedrange': True,
            'gridcolor': 'lightgrey',
            'gridwidth': 0.2,
            'griddash': 'dot',
            'visible': False
        },
        yaxis={
            'gridcolor': 'lightgrey',
            'gridwidth': 0.2,
            'griddash': 'dot',
            'visible': False
        },
        hovermode='x unified'
    )
    return pio.to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        config={'staticPlot': True, 'displayModeBar': False}
    ), len(values)