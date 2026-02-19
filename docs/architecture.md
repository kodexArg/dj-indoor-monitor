# 1. Arquitectura de Dominio y Sistema

El sistema está diseñado como una aplicación web monolítica moderna, utilizando Django como núcleo y tecnologías de renderizado del lado del servidor (SSR) potenciadas con interactividad dinámica vía HTMX. La arquitectura sigue un enfoque de capas claras para separar responsabilidades.

## 1.1. Diagrama de Arquitectura

```ascii
+-------------------+       +-------------------+       +-------------------+
|     Cliente       |       |   Servidor Web    |       |  Infraestructura  |
|    (Navegador)    | <---> |  (Django/Gunicorn)| <---> |   (Persistencia)  |
+-------------------+       +-------------------+       +-------------------+
| - HTML5 / CSS3    |       | - Core App Logic  |       | - PostgreSQL      |
| - HTMX            |       | - Data Processing |       |   (TimescaleDB)   |
| - Plotly.js       |       |   (Pandas)        |       | - Redis (Future)  |
| - Skeleton CSS    |       | - REST API (DRF)  |       +-------------------+
+-------------------+       +-------------------+
```

## 1.2. Capas del Sistema

### Capa de Presentación (Frontend)
El frontend es ligero y se basa en HTML estándar servido por Django.
*   **HTMX**: Gestiona la interactividad (carga de gráficos, actualizaciones en tiempo real) eliminando la necesidad de un framework SPA complejo. Realiza peticiones AJAX que devuelven HTML parcial.
*   **Plotly.js**: Librería de visualización ejecutada en el navegador para renderizar los gráficos interactivos generados por el backend.
*   **Estilos**: Utiliza `Skeleton CSS` y `Normalize.css` para un diseño minimalista y responsivo.

### Capa de Aplicación (Backend)
El núcleo del sistema es Django, ejecutado sobre Gunicorn (en producción) o el servidor de desarrollo.
*   **Gestión de Peticiones**: Enruta las solicitudes HTTP a las Vistas (Templates) o a la API REST.
*   **Procesamiento de Datos**: Utiliza `Pandas` para transformar, limpiar y agregar los datos crudos de los sensores antes de enviarlos al frontend o la API.
*   **API REST**: Expone endpoints para la ingestión de datos desde los dispositivos IoT (sensores) y para consultas externas.

### Capa de Persistencia (Base de Datos)
PostgreSQL actúa como la única fuente de verdad (SSOT).
*   **Modelo Híbrido**: Almacena tanto el modelo relacional (Habitaciones, Sensores) como las series temporales (DataPoints).
*   **Índices**: Se aprovechan índices compuestos para optimizar las consultas de rangos de tiempo y filtrado por sensor/métrica.

### Capa de Ingesta (IoT)
Los dispositivos sensores (p.ej., Raspberry Pi, ESP32) envían datos al sistema a través de la API REST (`POST /api/data-point/`).
*   **Alta Frecuencia**: El sistema está diseñado para soportar alta frecuencia de escritura.
*   **Validación Diferida**: Los datos se almacenan inmediatamente en la tabla `DataPoint` con validaciones mínimas para maximizar throughput.

## 1.3. Flujo de Datos

1.  **Ingesta (Escritura)**: Sensor -> API REST -> Validación Básica -> PostgreSQL.
2.  **Consulta (Vista Web)**: Usuario -> Navegador -> Django View -> Consulta DB -> Pandas (Procesamiento/Agregación) -> Renderizado HTML -> Respuesta.
3.  **Interactividad (Gráfico)**: Usuario -> Interacción UI -> HTMX Request -> Django View -> Generación de Gráfico -> HTML Parcial -> Inserción en DOM.
