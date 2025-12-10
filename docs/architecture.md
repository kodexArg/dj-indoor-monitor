# Arquitectura del Sistema

El sistema está diseñado como una aplicación web monolítica moderna, utilizando Django como núcleo y aprovechando tecnologías de renderizado del lado del servidor (SSR) potenciadas con interactividad dinámica vía HTMX.

## Diagrama de Arquitectura

```ascii
+-------------------+       +-------------------+       +-------------------+
|     Cliente       |       |   Servidor Web    |       |  Base de Datos    |
|    (Navegador)    | <---> |  (Django/Gunicorn)| <---> |   (PostgreSQL)    |
+-------------------+       +-------------------+       +-------------------+
| - HTML5 / CSS3    |       | - Core App Logic  |       | - Datos Sensores  |
| - HTMX            |       | - Data Processing |       | - Configuración   |
| - Plotly.js       |       |   (Pandas)        |       | - Usuarios        |
| - Skeleton CSS    |       | - REST API (DRF)  |       +-------------------+
+-------------------+       +-------------------+
```

## Componentes Principales

### 1. Cliente (Frontend)
El frontend es ligero y se basa en HTML estándar servido por Django.
*   **HTMX**: Maneja la interactividad (carga de gráficos, actualizaciones en tiempo real) sin necesidad de un framework SPA complejo (como React o Vue). Realiza peticiones AJAX que devuelven HTML parcial.
*   **Plotly.js**: Librería de visualización ejecutada en el navegador para renderizar los gráficos interactivos generados por el backend.
*   **Estilos**: Utiliza `Skeleton CSS` y `Normalize.css` para un diseño minimalista y responsivo.

### 2. Servidor de Aplicaciones (Backend)
El núcleo del sistema es Django, ejecutado sobre Gunicorn (en producción) o el servidor de desarrollo.
*   **Gestión de Peticiones**: Enruta las solicitudes HTTP a las Vistas (Templates) o a la API REST.
*   **Procesamiento de Datos**: Utiliza `Pandas` para transformar, limpiar y agregar los datos crudos de los sensores antes de enviarlos al frontend o la API.
*   **API REST**: Expone endpoints para la ingestión de datos desde los dispositivos IoT (sensores) y para consultas externas.

### 3. Capa de Persistencia (Base de Datos)
PostgreSQL actúa como la única fuente de verdad (SSOT).
*   Almacena tanto el modelo relacional (Habitaciones, Sensores) como las series temporales (DataPoints).
*   Se aprovechan índices compuestos para optimizar las consultas de rangos de tiempo y filtrado por sensor/métrica.

### 4. Ingesta de Datos (IoT)
Los dispositivos sensores (p.ej., Raspberry Pi, ESP32) envían datos al sistema a través de la API REST (`POST /api/data-point/`).
*   El sistema está diseñado para soportar alta frecuencia de escritura.
*   Los datos se validan y almacenan inmediatamente en la tabla `DataPoint`.

## Flujo de Datos

1.  **Escritura**: Sensor -> API REST -> Validación -> PostgreSQL.
2.  **Lectura (Vista Web)**: Usuario -> Navegador -> Django View -> Consulta DB -> Pandas (Procesamiento) -> Renderizado HTML -> Respuesta.
3.  **Lectura (Gráfico Interactivo)**: Usuario -> Interacción UI -> HTMX Request -> Django View -> Generación de Gráfico -> HTML Parcial -> Inserción en DOM.
