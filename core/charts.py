# charts.py

"""
Funciones para la generación de gráficos y visualizaciones.
"""
import plotly.graph_objects as go
import plotly.io as pio

def gauge_generator(value, metric, sensor):
    # Configuraciones predeterminadas para métricas de 't' y 'h'
    GAUGE_CONFIGS = {
        't': {
            'steps': [[0, 18], [18, 24], [24, 35]],
            'unit': '°C',
            'title': '',
            'colors': [
                'rgba(135, 206, 235, 0.8)',  # Azul frío
                'rgba(144, 238, 144, 0.6)',  # Verde claro (óptimo)
                'rgba(255, 99, 71, 0.8)'     # Rojo-naranja (caliente)
            ]
        },
        'h': {
            'steps': [[0, 40], [40, 60], [60, 90]],
            'unit': '%',
            'title': '',
            'colors': [
                'rgba(255, 198, 109, 0.8)',  # Amarillo-naranja (seco)
                'rgba(152, 251, 152, 0.6)',  # Verde menta (óptimo)
                'rgba(100, 149, 237, 0.8)'   # Azul (húmedo)
            ]
        }
    }
    
    config = GAUGE_CONFIGS.get(metric)
    steps = config['steps']
    title = f"{config['title']} {sensor}"
    
    fig = go.Figure()
    
    max_value = max(steps[2][1], value)
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0.2, 1]},
        number={
            'font': {'size': 28, 'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'}, 
            'suffix': f" {config['unit']}",
            'valueformat': '.1f'
        },
        gauge={
            'axis': {
                'range': [0, max_value],
                'tickwidth': 1,
                'tickcolor': "#888888",
                'tickfont': {'size': 8, 'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'},
                'tickmode': 'linear',
                'dtick': max_value/5
            },
            'bar': {'color': "rgba(150, 150, 150, 0.5)"},
            'bgcolor': "white",
            'borderwidth': 0,
            'steps': [
                {'range': steps[0], 'color': config['colors'][0]},
                {'range': steps[1], 'color': config['colors'][1]},
                {'range': steps[2], 'color': config['colors'][2]}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.8,
                'value': value
            }
        }
    ))

    fig.update_layout(
        height=160,
        width=320,
        margin=dict(l=15, r=15, t=50, b=5),
        paper_bgcolor="white",
        font={'color': "#666666", 'family': "Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif"},
        showlegend=False,
        title={
            'text': title,
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {
                'size': 16,
                'color': '#5f9b62',
                'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'
            }
        }
    )

    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        config={'staticPlot': True, 'displayModeBar': False}
    )
