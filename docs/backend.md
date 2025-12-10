# Backend

El backend del proyecto está construido sobre Django y tiene la responsabilidad de gestionar la ingestión de datos, procesar consultas analíticas complejas y servir tanto la API REST como las vistas HTML renderizadas en el servidor.

## Estructura de Aplicaciones

El proyecto sigue una estructura monolítica centrada en una aplicación principal:

*   **core**: Contiene toda la lógica de negocio, modelos, vistas y API.
*   **project**: Directorio de configuración de Django (`settings.py`, `asgi.py`, `wsgi.py`).

## API REST (Django REST Framework)

La API se expone principalmente a través de `DataPointViewSet` en `core/api.py`, proporcionando acceso a los datos de los sensores.

### DataPointViewSet
Controlador principal que gestiona las operaciones CRUD y acciones especializadas para series temporales.

*   **Endpoints Estándar**: Acceso RESTful básico a `DataPoint`.
*   **Acción `latest`**: Devuelve la última lectura registrada para cada sensor.
*   **Acción `timeframed`**: Endpoint analítico que permite obtener datos agregados y re-muestreados en intervalos de tiempo definidos (e.g., promedios por hora). Utiliza Pandas para realizar agregaciones temporales eficientes.

### Patrón "Processor"
Para mantener las vistas limpias, la lógica de consulta compleja se delega a clases procesadoras (`ListData`, `LatestData`, `TimeframedData`) que heredan de `DataPointQueryProcessor`. Estas clases manejan:
1.  Filtrado avanzado.
2.  Agrupación de datos.
3.  Cálculo de agregaciones (min, max, media).
4.  Formateo de respuesta.

## Vistas y Renderizado (Django Templates + HTMX)

El backend sirve vistas HTML tradicionales que se enriquecen dinámicamente utilizando HTMX.

*   **Vistas Basadas en Clases (CBVs)**: Se utilizan `TemplateView` y `View` para estructurar la lógica de presentación.
    *   `SensorsView`: Panel principal.
    *   `ChartsView` / `InteractiveView`: Visualización de gráficos históricos.
    *   `VPDView`: Cálculo y visualización del Déficit de Presión de Vapor.
*   **Integración HTMX**:
    *   Endpoints como `GenerateSensorView` y `GenerateGaugeView` devuelven fragmentos de HTML (gráficos o componentes UI) en lugar de JSON o páginas completas.
    *   Esto permite cargas asíncronas y actualizaciones parciales de la interfaz sin recargar la página completa.

## Procesamiento de Datos y Análisis

El backend integra fuertemente `pandas` para manipular series temporales.

*   **DataPointDataFrameBuilder**: Clase utilitaria para convertir QuerySets de Django en DataFrames de Pandas.
*   **Operaciones**:
    *   **Resampling**: Ajuste de la frecuencia de los datos (e.g., convertir datos brutos a promedios de 15 minutos).
    *   **Pivoting**: Transformación de datos para análisis comparativo (e.g., alinear temperatura y humedad).
    *   **Cálculo de VPD**: Lógica de negocio para calcular métricas derivadas como el VPD basándose en temperatura y humedad.

## Utilidades

*   **Logging**: Implementado con `loguru` para un registro estructurado y detallado de las operaciones.
*   **Filtros**: Uso de `django-filter` para permitir consultas flexibles vía parámetros URL en la API.
