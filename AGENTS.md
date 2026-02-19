# AGENTS.md

> **Guía maestra para Agentes de IA trabajando en este proyecto (Dj Indoor Monitor).**
> Este documento actúa como la fuente de verdad técnica y arquitectónica.

## 1. Visión General del Proyecto
Este sistema es un monitor de ambiente interior construido sobre **Django Monolítico**. Su función principal es la ingesta, almacenamiento y visualización de datos de series temporales (temperatura, humedad, luz, etc.) provenientes de sensores IoT.

El sistema prioriza la **eficiencia en escrituras** (ingesta de datos) y la **visualización performante** de grandes volúmenes de datos históricos.

## 2. Dominio
El núcleo del negocio se modela alrededor de la estructura física y la recolección de métricas.

*   **Room (Habitación)**: Unidad lógica de agrupación física (`core/models.py`). Representa un espacio monitoreado.
*   **Sensor**: Dispositivo físico asociado a una `Room`.
*   **DataPoint**: La unidad atómica de información. Representa una lectura en un momento del tiempo (`timestamp`, `sensor`, `metric`, `value`).

### Reglas de Negocio Críticas
*   **Desacoplamiento de Escritura**: El modelo `DataPoint` **NO** tiene una ForeignKey directa a `Sensor`. Utiliza `sensor` (string) para permitir una ingesta masiva rápida y sin validaciones de integridad referencial costosas en tiempo real. La relación se resuelve lógicamente en tiempo de lectura (vistas/API) mediante mapeos en memoria (ver `core/api.py`).
*   **Métricas**: Identificadas por caracteres simples ('t' para temperatura, 'h' para humedad, etc.).

## 3. Interfaces

### 3.1. API REST (Ingesta y Consulta)
Implementada con **Django Rest Framework (DRF)** en `core/api.py`.

*   **Endpoints Principales**:
    *   `POST /api/data-point/`: Ingesta de datos crudos.
    *   `GET /api/data-point/latest/`: Últimos valores por sensor.
    *   `GET /api/data-point/timeframed/`: Datos agregados/resampleados para consultas históricas eficientes.
*   **Patrones de API**:
    *   Uso intensivo de `Pandas` en el backend (`core/api.py`, `core/utils.py`) para realizar agregaciones temporales (resampling) ante consultas de rangos amplios.
    *   Soporte de filtros complejos: rango de fechas, lista de sensores, métricas específicas.

### 3.2. Interfaz de Usuario (Visualización)
Implementada con **Django Templates + HTMX + Plotly**.

*   **Enfoque**: Renderizado híbrido. La estructura base es SSR (Server Side Rendering), pero los gráficos y datos dinámicos se cargan/actualizan vía **HTMX** para evitar recargas completas.
*   **Visualización**: Se utiliza `Plotly` generado en el backend (`core/charts.py`) que retorna HTML/JS listo para inyectar en el DOM.
*   **Optimización de Vistas**: `GenerateSensorView` implementa algoritmos de "downsampling" (`calculate_optimal_frequency`) para reducir miles de puntos de datos a una cantidad visualizable (~120 puntos) antes de graficar.

## 4. Almacenamiento
*   **Motor**: PostgreSQL (vía `psycopg2`).
*   **Estrategia de Índices**: La tabla `core_datapoint` tiene índices compuestos agresivos (`sensor, timestamp`, `metric, timestamp`) para optimizar las consultas de rangos de tiempo, que son las más críticas del sistema.

## 5. Arquitectura y Patrones Técnicos
*   **Monolito Modular**: Todo el código vive en `core`, pero separa claramente `models` (datos), `views` (UI), `api` (REST) y `utils/charts` (lógica de negocio/transformación).
*   **Data Processing on Read**: A diferencia de sistemas que pre-agregan datos al escribir, este sistema ingesta crudo y procesa/agrega en tiempo de lectura usando Pandas, aprovechando la caché y la potencia del servidor web.
*   **Logging**: Sistema robusto de logging (`loguru` y `logging` nativo) para trazar tiempos de ejecución de endpoints (`endpoints_logger`), vital para monitorear latencia en visualizaciones.

## 6. Comandos de Desarrollo
*   **Iniciar Servidor**: `python manage.py runserver`
*   **Migraciones**: `python manage.py migrate`
*   **Tests**: `pytest` (Configurado en `pytest.ini` / `requirements.txt` incluye `pytest-django`).

## 7. Referencias de Código Clave
*   **Modelos**: `core/models.py`
*   **Lógica de API/Agregación**: `core/api.py` (Clases `ListData`, `LatestData`, `TimeframedData`).
*   **Generación de Gráficos**: `core/charts.py` y `core/views.py`.
*   **Utilidades de Pandas**: `core/utils.py`.
