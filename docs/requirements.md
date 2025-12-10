# Requerimientos y Dependencias

Este documento detalla las librerías y dependencias clave utilizadas en el proyecto, categorizadas por su función principal dentro de la arquitectura del sistema.

## Framework Web y API

*   **Django**: Framework web de alto nivel que constituye el núcleo del backend. Facilita el desarrollo rápido, diseño limpio y pragmático.
*   **Django REST Framework (DRF)**: Herramienta flexible y potente para construir APIs Web. Utilizado para exponer endpoints de datos consumibles por el frontend o servicios externos.
*   **django-filter**: Permite a los usuarios filtrar conjuntos de consultas dinámicamente basándose en parámetros de URL.
*   **django-cors-headers**: Aplicación Django para gestionar las cabeceras de Cross-Origin Resource Sharing (CORS), permitiendo solicitudes desde otros dominios.

## Frontend e Interactividad

*   **django-htmx**: Extensión para integrar HTMX con Django. Permite realizar actualizaciones dinámicas del DOM mediante interacciones AJAX declarativas directamente en HTML, sin necesidad de escribir JavaScript complejo.

## Procesamiento de Datos y Visualización

*   **Pandas**: Librería fundamental para el análisis y manipulación de datos. Se utiliza para procesar series temporales y estructuras de datos complejas provenientes de los sensores.
*   **NumPy**: Soporte para arreglos y matrices multidimensionales, junto con una colección de funciones matemáticas de alto nivel.
*   **Plotly**: Librería de gráficos interactivos. Se emplea para generar visualizaciones de datos ricas y responsivas en el frontend.
*   **Kaleido**: Motor de generación de imágenes estáticas para Plotly, útil para exportar gráficos.

## Servidor y Despliegue

*   **Gunicorn**: Servidor HTTP WSGI para UNIX. Actúa como servidor de aplicaciones en entornos de producción.
*   **Uvicorn**: Servidor ASGI rápido, necesario para manejar capacidades asíncronas si se requieren, y compatible con Gunicorn.
*   **asgiref**: Paquete de referencia para la especificación ASGI.

## Base de Datos

*   **psycopg2**: Adaptador de base de datos PostgreSQL para Python. Es el conector estándar y más robusto para interactuar con bases de datos PostgreSQL desde Django.

## Utilidades y Configuración

*   **python-dotenv**: Permite cargar variables de entorno desde un archivo `.env`, facilitando la gestión de configuraciones sensibles y específicas del entorno.
*   **Loguru**: Librería de logging que simplifica la emisión y gestión de registros de eventos del sistema.
*   **PyYAML**: Analizador y emisor de YAML para Python, utilizado probablemente para archivos de configuración.
*   **Requests**: Librería HTTP elegante y simple para realizar peticiones a servicios externos.

## Testing y Calidad de Código

*   **pytest**: Framework de pruebas maduro y completo.
*   **pytest-django**: Plugin para `pytest` que proporciona herramientas específicas para probar aplicaciones Django.
*   **pytest-cov**: Plugin para generar reportes de cobertura de código.
*   **Coverage**: Herramienta para medir la cobertura de código de los programas en Python.

## Gráficos e Imágenes

*   **CairoSVG**: Convertidor de SVG a formatos raster/vectoriales.
*   **Pillow**: Librería de procesamiento de imágenes de Python (fork de PIL).
