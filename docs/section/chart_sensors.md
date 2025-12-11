# Análisis Funcional: Página de Sensores (SensorsView)

## Visión General
La página "Sensores" (`/charts/sensors/`) actúa como un tablero de mando (dashboard) que muestra gráficos individuales para cada sensor y métrica configurados en el sistema. Su objetivo es proporcionar una vista rápida y detallada del estado reciente de todos los dispositivos, organizados por ubicación (Sala).

## Arquitectura de la Página

### 1. Estructura de Navegación y Filtros
La interfaz presenta controles superiores para definir el contexto temporal de los datos visualizados:
*   **Selector de Timeframe (Rango de Tiempo)**: Un conjunto de botones (`1'`, `30'`, `1h`, `4h`, `1d`) que permiten al usuario cambiar la ventana de tiempo de los datos históricos mostrados.
    *   **Comportamiento Actual**: Al hacer clic, se realiza una recarga completa de la página (`GET request`) pasando el parámetro `timeframe` en la URL.
    *   **Problema Identificado**: La recarga completa es ineficiente y lenta, ya que reconstruye toda la estructura de la página y reinicia el proceso de carga asíncrona de todos los gráficos.

### 2. Organización del Contenido
El cuerpo principal de la página está estructurado jerárquicamente:
1.  **Nivel Sala (Room)**: Los sensores se agrupan visualmente por la sala a la que pertenecen. Cada sala tiene un encabezado distintivo.
2.  **Nivel Métrica/Sensor**: Dentro de cada sala, se iteran las métricas disponibles (Temperatura, Humedad, Luz, Sustrato) y, para cada una, se muestran los sensores que reportan dicha métrica.

### 3. Mecánica de Carga de Gráficos (Lazy Loading con HTMX)
Para mejorar el tiempo de respuesta inicial (Time to First Byte - TTFB), la página utiliza un patrón de "Carga Diferida" (Lazy Loading) implementado con HTMX:

1.  **Renderizado Inicial**: El servidor (`SensorsView`) renderiza la estructura HTML "esqueleto" (títulos de salas, contenedores de gráficos vacíos). No se generan gráficos en este paso.
    *   *Backend*: `prepare_sensors_view_data` identifica qué sensores están activos y estructura el diccionario de datos `data[room][metric][sensors]`.
2.  **Disparadores HTMX**: Cada contenedor de gráfico (`div.chart-container`) tiene atributos HTMX:
    *   `hx-trigger="load"`: Se activa automáticamente tan pronto como el elemento aparece en el DOM.
    *   `hx-post="/generate_sensor/"`: Solicita al servidor el HTML específico para ese gráfico.
    *   `hx-vals`: Envía los parámetros necesarios (`sensor`, `timeframe`, `metric`).
3.  **Generación Bajo Demanda**: El servidor recibe múltiples peticiones POST paralelas (una por gráfico). La vista `GenerateSensorView`:
    *   Consulta la base de datos para ese sensor/métrica/rango específico.
    *   Procesa los datos (resampling con Pandas).
    *   Genera el HTML del gráfico usando Plotly.
    *   Devuelve el fragmento HTML.
4.  **Inserción en DOM**: HTMX reemplaza el contenido del contenedor (el spinner de carga) con el gráfico renderizado.

## Análisis de Flujo de Datos y Rendimiento

### Cuellos de Botella Actuales
1.  **Recarga Completa por Timeframe**: Cambiar el rango de tiempo (e.g., de 1h a 4h) obliga al navegador a destruir y recrear todo el DOM, disparando nuevamente decenas de peticiones HTMX simultáneas. Esto satura el navegador y el servidor.
2.  **Carga "En Cascada" Masiva**: Al cargar la página, si existen 20 sensores con 2 métricas cada uno, se disparan 40 peticiones AJAX casi simultáneas. Aunque asíncronas, esto puede bloquear el hilo principal del navegador (renderizado de Plotly) y saturar los workers del servidor Gunicorn/Django.
3.  **Falta de Filtrado por Contexto**: Actualmente se cargan *todas* las salas. Si el usuario solo quiere ver "Invernadero 1", el sistema desperdicia recursos procesando y renderizando "Invernadero 2", "Secado", etc.

### Propuesta de Mejora: Filtro de Sala
La adición de un filtro de "Sala" (`Room Selector`) transformará la mecánica de la página:
*   **UI**: Un selector junto a los botones de timeframe.
*   **Lógica**:
    *   Debe persistir el estado del timeframe seleccionado.
    *   Al seleccionar una sala, la página debe recargarse (o actualizarse vía HTMX) para mostrar *únicamente* los contenedores correspondientes a esa sala.
    *   Esto reducirá drásticamente el número de peticiones `/generate_sensor/` disparadas, mejorando la velocidad percibida y real.

## Elementos de UI/UX Clave
*   **`div#toggle-buttons-timeframe`**: Contenedor de botones de tiempo.
*   **`div.room-title-wrapper`**: Encabezado de sección de sala.
*   **`div.chart-container`**: Elemento "placeholder" que inicia la carga asíncrona. Contiene un spinner visual (`div.loading`).

## Conclusión
La página funciona bajo un modelo híbrido eficiente (Skeleton + Lazy Load), pero carece de granularidad en el control de carga. La implementación del filtro de sala es crítica para la escalabilidad, ya que permite al usuario (y al sistema) enfocar recursos solo en los datos relevantes.
