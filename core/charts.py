import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path
from loguru import logger
import numpy as np
import pandas as pd
from plotly.offline import plot
import plotly.colors as pcolors
from plotly.subplots import make_subplots

# Get project root directory
BASE_DIR = Path(__file__).resolve().parent.parent # This BASE_DIR is used by the module itself.

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

# New constants for generate_interactive_multi_metric_chart
INTERACTIVE_CHART_METRIC_NAMES = {
    't': 'Temperatura (°C)',
    'h': 'Humedad (%)',
    'l': 'Luz (lux)',
    's': 'Sustrato (%)'
}

INTERACTIVE_CHART_BAND_CFG = {
    't': {
        'steps': [18, 24, 40],
        'colors': ['rgba(135, 206, 235, 0.2)', 'rgba(144, 238, 144, 0.2)', 'rgba(255, 99, 71, 0.2)']
    },
    'h': {
        'steps': [40, 55, 100],
        'colors': ['rgba(255, 198, 109, 0.2)', 'rgba(152, 251, 152, 0.2)', 'rgba(100, 149, 237, 0.2)']
    },
    'l': {
        'steps': [0, 900, 1000],
        'colors': ['rgba(105, 105, 105, 0.1)', 'rgba(255, 255, 153, 0.2)']
    },
    's': {
        'steps': [0, 30, 60, 100],
        'colors': ['rgba(255, 198, 109, 0.2)', 'rgba(152, 251, 152, 0.2)', 'rgba(100, 149, 237, 0.2)']
    }
}

def gauge_plot(value, metric, sensor, timestamp=None):
    """Genera HTML de gráfico de medidor para una métrica de sensor."""
    metric_cfg = METRICS_CFG.get(metric)
    if not metric_cfg:
        return "<div>Invalid metric</div>"

    steps = metric_cfg['steps']
    main_title = f"{metric_cfg['title']} en {metric_cfg['unit']}"
    sensor_name = str(sensor).title()

    fig = go.Figure()
    max_value = steps[-1]

    # Generar 'steps' del medidor dinámicamente
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

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0.15, 1]},
        number={
            'font': {'size': 24,
                     'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'},
            'suffix': f" {metric_cfg['unit']}",
            'valueformat': '.1f' if metric != 'l' else '.0f' # Sin decimales para lux
        },
        gauge={
            'axis': {
                'range': [0, max_value],
                'tickwidth': 1,
                'tickcolor': "#888888",
                'tickfont': {'size': 10,
                             'family': 'Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif'},
                'tickmode': 'linear',
                'dtick': max_value / 5 # 5 ticks en el eje
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
    """Genera HTML de gráfico de línea para datos de sensor, con bandas de color para rangos óptimos."""
    try:
        if df.empty:
            logger.warning("DataFrame vacío")
            return f'<div>No hay datos para {sensor} - {metric}</div>', 0
        
        df = df.dropna(subset=['value'])
        processed_values = df['value'].tolist()
        processed_timestamps = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()
            
        metric_cfg = METRICS_CFG.get(metric, {'brand_color': '#808080', 'title': metric.title()})
        
        fig = go.Figure()
        
        # Añadir bandas de fondo si están configuradas
        if "steps" in metric_cfg:
            steps = metric_cfg["steps"]
            colors = metric_cfg["color_bars_gradient"]
            shapes = []
            if steps[0] != 0: # Banda inicial si el primer step no es 0
                shapes.append({
                    "type": "rect", "xref": "paper", "yref": "y",
                    "x0": 0, "x1": 1, "y0": 0, "y1": steps[0],
                    "fillcolor": colors[0] if len(colors) > 0 else 'rgba(200,200,200,0.2)',
                    "opacity": 0.07, "line": {"width": 0},
                })
            for i in range(1, len(steps)): # Bandas restantes
                fillcolor = colors[i] if i < len(colors) else 'rgba(200,200,200,0.2)'
                shapes.append({
                    "type": "rect", "xref": "paper", "yref": "y",
                    "x0": 0, "x1": 1, "y0": steps[i-1], "y1": steps[i],
                    "fillcolor": fillcolor, "opacity": 0.07, "line": {"width": 0},
                })
            # Ajustar rango Y para mejor visualización de bandas
            min_y = (0 + steps[0]) / 2 
            max_y = steps[-1] * 1.05 if len(steps) > 1 else steps[0] * 1.5
            y_range = [min_y, max_y]
        else:
            shapes = []
            y_range = None # Rango Y automático si no hay bandas
        
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
            height=None, # Permitir autosize
            width=None,  # Permitir autosize
            autosize=True,
            margin=dict(l=90, r=20, t=20, b=20),
            xaxis={
                'type': 'date',
                'fixedrange': True,
                'tickmode': 'auto',
                'showgrid': True, 'gridcolor': 'lightgrey', 'gridwidth': 0.5, 'griddash': 'dot',
                'visible': True,
                'range': [start_date.isoformat(), end_date.isoformat()] # Fijar rango del eje X
            },
            yaxis={
                'fixedrange': True,
                'range': y_range,
                'tickmode': 'auto',
                'showgrid': True, 'gridcolor': 'lightgrey', 'gridwidth': 0.5, 'griddash': 'dot',
                'visible': True,
                'side': 'right' # Eje Y a la derecha
            },
            hovermode='x unified',
            annotations=[
                {
                    "x": -0.1, "y": 0.5, "xref": "paper", "yref": "paper",
                    "text": f"<b>{metric_cfg['title']} en {metric_cfg['unit']}</b><br><span style='font-size:0.8em;'>sensor {sensor.upper()}</span>",
                    "showarrow": False, "textangle": -90,
                    "xanchor": "left", "yanchor": "middle",
                    "font": {"size": 16, "color": "#5f9b62", "family": "Raleway, HelveticaNeue, Helvetica Neue, Helvetica, Arial, sans-serif"}
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
    """Calcula Déficit de Presión de Vapor (VPD) en kPa."""
    # Fórmula de VPD: svp (presión de vapor de saturación) - vp (presión de vapor actual)
    svp = 0.6108 * np.exp((17.27 * t) / (t + 237.3)) # Ecuación de Tetens para SVP en kPa
    vp = svp * (h / 100) # VP actual basada en humedad relativa
    return svp - vp

def vpd_plot(data, temp_min=10, temp_max=40, hum_min=20, hum_max=80):
    """Genera HTML de gráfico VPD, mostrando puntos de salas contra bandas objetivo de VPD."""
    filtered_data = [
        (room, float(temp), float(hum))
        for room, temp, hum in data
        if temp_min <= temp <= temp_max and hum_min <= hum <= hum_max
    ]

    if not filtered_data:
        return '<div>Sin datos en el rango especificado</div>'

    vpd_bands = [
        ("Muy Húmedo", 0, 0.4, "rgba(245, 230, 255, 0.2)"),
        ("Propagación", 0.4, 0.8, "rgba(195, 230, 215, 0.5)"),
        ("Vegetación", 0.8, 1.2, "rgba(255, 225, 180, 0.5)"),
        ("Flora", 1.2, 1.6, "rgba(255, 200, 150, 0.5)"),
        ("Muy Seco", 1.6, 10.0, "rgba(255, 100, 100, 0.025)")
    ]
    temperatures = np.linspace(temp_min, temp_max, 200) # Rango de temperaturas para dibujar bandas

    # Función para calcular humedad (h) desde temperatura (t) y VPD
    def calc_hum_from_vpd(t, vpd):
        svp = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
        h = 100 * (1 - vpd / svp) if svp > 0 else 100 # Evitar división por cero
        return max(hum_min, min(hum_max, h)) # Limitar humedad a rango visible

    fig = go.Figure()
    # Dibujar bandas de VPD en el gráfico
    for band_name, vpd_min_band, vpd_max_band, color in vpd_bands:
        h_upper = [calc_hum_from_vpd(t, vpd_min_band) for t in temperatures]
        h_lower = [calc_hum_from_vpd(t, vpd_max_band) for t in temperatures]
        fig.add_trace(go.Scatter(
            x=h_upper, y=temperatures, mode='lines', line=dict(width=0),
            fillcolor=color, showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=h_lower, y=temperatures, mode='lines', line=dict(width=0),
            fill='tonexty', fillcolor=color, name=band_name,
            showlegend=not band_name.startswith("Muy") # No mostrar en leyenda bandas extremas
        ))

    # Agregar puntos de datos (salas) al gráfico
    for room_name, temp, hum in filtered_data:
        current_vpd = calculate_vpd(temp, hum)
        fig.add_trace(go.Scatter(
            y=[temp], x=[hum], mode='markers+text',
            marker=dict(size=10, color='black'),
            text=[f"Sala {room_name} {current_vpd:.1f} kPa"],
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
            title='Humedad Relativa (%HR)', range=[hum_min, hum_max], dtick=10,
            gridcolor='rgba(200, 200, 200, 0.2)', side='bottom', tickfont=dict(size=10)
        ),
        yaxis=dict(
            title='Temperatura (°C)', range=[temp_min, temp_max], dtick=5,
            gridcolor='rgba(200, 200, 200, 0.2)', side='right', tickfont=dict(size=10)
        ),
        plot_bgcolor='white', margin=dict(l=10, r=10, t=10, b=10), height=600
    )
    return pio.to_html(fig, include_plotlyjs=True, full_html=False, config={'staticPlot': True})

def generate_interactive_multi_metric_chart(data_df, metrics, by_room=False, timeframe='1T', start_date=None, end_date=None):
    if data_df.empty:
        logger.warning("generate_interactive_multi_metric_chart: Empty DataFrame, returning no data message")
        return "<div class='no-data-alert'>No hay datos disponibles para este período o los sensores fueron filtrados.</div>", 0
    
    logger.debug(f"generate_interactive_multi_metric_chart: Processing DataFrame with {len(data_df)} rows for chart generation.")
    
    base_colors = pcolors.qualitative.Plotly 
    
    fig = make_subplots(
        rows=len(metrics), 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
    )
    
    group_column = 'room' if by_room else 'sensor'
    if group_column not in data_df.columns:
        logger.error(f"generate_interactive_multi_metric_chart: Missing '{group_column}' column in DataFrame")
        return "<div class='no-data-alert'>Error: Columna de agrupación requerida ausente.</div>", 0
    
    plotted_points = 0
    unique_items = sorted(data_df[group_column].unique())
    color_map = {item_name: base_colors[i % len(base_colors)] for i, item_name in enumerate(unique_items)}

    logger.debug(f"generate_interactive_multi_metric_chart: Plotting for {len(unique_items)} unique {group_column}s: {unique_items}")
    
    for i, metric_code in enumerate(metrics, 1):
        if metric_code in INTERACTIVE_CHART_BAND_CFG:
            steps = INTERACTIVE_CHART_BAND_CFG[metric_code]['steps']
            colors = INTERACTIVE_CHART_BAND_CFG[metric_code]['colors']
            
            if steps[0] > 0:
                fig.add_shape(
                    type="rect",
                    xref=f"x{i}", yref=f"y{i}",
                    x0=start_date, x1=end_date,
                    y0=0, y1=steps[0],
                    fillcolor=colors[0], opacity=0.5,
                    layer="below", line_width=0,
                    row=i, col=1
                )
            
            for j in range(1, len(steps)):
                fig.add_shape(
                    type="rect",
                    xref=f"x{i}", yref=f"y{i}",
                    x0=start_date, x1=end_date,
                    y0=steps[j-1], y1=steps[j],
                    fillcolor=colors[min(j, len(colors)-1)], opacity=0.5,
                    layer="below", line_width=0,
                    row=i, col=1
                )
        
        if metric_code not in data_df.columns:
            logger.warning(f"generate_interactive_multi_metric_chart: Metric '{metric_code}' not in DataFrame columns: {data_df.columns.tolist()}")
            continue
            
        for item_name, group_data in data_df.groupby(group_column):
            valid_data = group_data.dropna(subset=[metric_code])
            if valid_data.empty:
                continue
                
            valid_data = valid_data.sort_values(by='timestamp')
            plotted_points += len(valid_data)
            item_color = color_map.get(item_name, '#808080') 
            current_metric_name = INTERACTIVE_CHART_METRIC_NAMES.get(metric_code, metric_code.upper())
            
            fig.add_trace(
                go.Scatter(
                    x=valid_data['timestamp'],
                    y=valid_data[metric_code],
                    mode='lines+markers',
                    name=f"{item_name} - {current_metric_name}",
                    line=dict(color=item_color, width=1.5),
                    marker=dict(size=3, color=item_color),
                    hovertemplate=f"{item_name} ({current_metric_name}): %{{y:.1f}}<extra></extra>"
                ),
                row=i, col=1
            )
    
    if plotted_points == 0:
        logger.warning("generate_interactive_multi_metric_chart: No points plotted. DataFrame might be empty or all items filtered.")
        return "<div class='no-data-alert'>No hay datos para mostrar después del filtrado.</div>", 0
    
    fig.update_layout(
        title=None, 
        height=467 * len(metrics),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=80, r=80, t=50, b=50),
        hovermode='closest',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1, 
            xanchor="center",
            x=0.5,
            traceorder="normal"
        ),
        autosize=True,
    )
    
    for i_ax in range(1, len(metrics) + 1):
        fig.update_xaxes(
            range=[start_date, end_date],
            showticklabels=True, 
            showgrid=True, gridwidth=1, gridcolor='rgba(211,211,211,0.5)', 
            showline=True, linewidth=1, linecolor='lightgreen', mirror=True,
            row=i_ax, col=1,
            tickfont=dict()
        )
        
        fig.update_yaxes(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='rgba(211,211,211,0.5)', 
            showline=True, 
            linewidth=1, 
            linecolor='lightgreen', 
            mirror=True,
            row=i_ax, 
            col=1,
            tickfont=dict(),
            tickformat=".1f",
            ticks="outside",
            showticklabels=True,
        )
        
        if metrics[i_ax-1] in INTERACTIVE_CHART_METRIC_NAMES:
            fig.update_yaxes(
                title_text=INTERACTIVE_CHART_METRIC_NAMES[metrics[i_ax-1]], 
                title_standoff=15,
                row=i_ax, 
                col=1
            )
    
    fig.update_xaxes(title_text=None, row=len(metrics), col=1)
    
    logger.debug(f"generate_interactive_multi_metric_chart: Generated chart with {plotted_points} points")
    return fig.to_html(include_plotlyjs='cdn', full_html=False, config={
        'responsive': True,
        'displayModeBar': False,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
    }), plotted_points