import plotly.graph_objects as go
import plotly.io as pio

def gauge_generator(value, metric, sensor):
    GAUGE_CONFIGS = {
        't': {
            'steps': [(0, 18), (18, 24), (24, 40)],
            'unit': '°C',
            'title': 'Temperatura',
            'colors': [
                'rgba(135, 206, 235, 0.8)',
                'rgba(144, 238, 144, 0.6)',
                'rgba(255, 99, 71, 0.8)',
            ]
        },
        'h': {
            'steps': [(0, 40), (40, 55), (55, 100)],
            'unit': '%',
            'title': 'Humedad',
            'colors': [
                'rgba(255, 198, 109, 0.8)',
                'rgba(152, 251, 152, 0.6)',
                'rgba(100, 149, 237, 0.8)',
            ]
        },
        'l': {
            'steps': [(0, 900), (900, 1000)],
            'unit': 'lum',
            'title': 'Luz',
            'colors': [
                'rgba(105, 105, 105, 0.2)',
                'rgba(255, 255, 153, 0.6)'
            ]
        },
        's': {
            'steps': [(0, 30), (30, 60), (60, 100)],
            'unit': '%',
            'title': 'Sustrato',
            'colors': [
                'rgba(255, 198, 109, 0.8)',
                'rgba(152, 251, 152, 0.6)',
                'rgba(100, 149, 237, 0.8)',
            ]
        }
    }

    config = GAUGE_CONFIGS.get(metric)
    if not config:
        return "<div>Invalid metric</div>"

    steps = config['steps']

    # Título principal: Título de la métrica
    main_title = config['title']

    # Subtítulo: Nombre del sensor (convertido a Title Case)
    sensor_name = str(sensor).title()


    fig = go.Figure()
    max_value = steps[-1][1]

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0.15, 1]}, 
        number={
            'font': {'size': 26,
                     'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'},
            'suffix': f" {config['unit']}",
            'valueformat': '.1f' if metric != 'l' else '.0f'
        },
        gauge={
            'axis': {
                'range': [0, max_value],
                'tickwidth': 1,
                'tickcolor': "#888888",
                'tickfont': {'size': 8,
                             'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'},
                'tickmode': 'linear',
                'dtick': max_value / 5
            },
            'bar': {'color': "rgba(150, 150, 150, 0.5)"},
            'bgcolor': "white",
            'borderwidth': 0,
            'steps': [
                {'range': step, 'color': config['colors'][i]} for i, step in enumerate(steps)
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.8,
                'value': value
            }
        }
    ))

    fig.update_layout(
        height=180,
        width=220,
        margin=dict(l=20, r=20, t=50, b=0),
        paper_bgcolor="white",
        font={'color': "#666666",
                 'family': "Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif"},
        showlegend=False,
        title={
            'text': f"<b>{main_title}</b><br><span style='font-size:0.7em;'>sensor {sensor_name}</span>",  # Título y subtítulo
            'y': 0.90,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {
                'size': 14,
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