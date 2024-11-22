# dj-indoor-monitor

## Propósito del Proyecto
"dj-indoor-monitor" es un sistema de monitoreo en tiempo real para datos ambientales de temperatura y humedad, recolectados desde dispositivos Raspberry Pi. Su objetivo es proporcionar una interfaz web funcional y dinámica que permita a los usuarios visualizar estos datos de forma clara y accesible.

## Estructura de Datos
Los datos se almacenan en un modelo llamado `SensorData` que contiene:
- **timestamp**: Fecha y hora del registro (e.g., `"2024-11-19T12:34:56Z"`).
- **rpi**: Identificación única del dispositivo Raspberry Pi (e.g., `"raspberry-pi-001"`).
- **t**: Temperatura medida en grados Celsius (e.g., `24.5`).
- **h**: Humedad relativa en porcentaje (e.g., `60.3`).

Estos datos se utilizan para gráficos interactivos y tablas dinámicas.

## Tecnologías Utilizadas
El proyecto emplea una combinación de tecnologías modernas para asegurar robustez, escalabilidad e interactividad:
- **Django** como framework principal para el backend y manejo de vistas.
- **Django REST Framework (DRF)** para exponer una API que permite consultas y envío de datos desde sensores.
- **Plotly** para la visualización de datos en gráficos interactivos.
- **HTMX** para actualizar componentes del frontend dinámicamente sin necesidad de recargar la página.
- **Loguru** para un registro detallado de eventos y errores, lo que facilita el monitoreo y depuración.

## Interactividad y Actualización
La interfaz está diseñada para reflejar cambios en los datos automáticamente, proporcionando tablas y gráficos que presentan información en tiempo real basada en la actividad de los sensores.

## Configuración Modular y Seguridad
La configuración del proyecto está centralizada en un archivo `.env`, donde se especifican variables sensibles como la clave secreta de Django (`SECRET_KEY`), las credenciales de la base de datos y las configuraciones de entorno. Esto permite una transición fluida entre entornos de desarrollo y producción.

## API para Sensores
El sistema permite que los dispositivos Raspberry Pi envíen datos mediante una API RESTful implementada con DRF. Los datos enviados son validados y almacenados en la base de datos para su análisis posterior.

## Almacenamiento de Datos
Por defecto, se utiliza SQLite para almacenamiento local, pero el proyecto está preparado para PostgreSQL según las configuraciones definidas en `.env`. Esto asegura que el sistema pueda escalar con facilidad en entornos productivos.

## Visualización de Datos
Las visualizaciones incluyen gráficos dinámicos de temperatura y tablas actualizadas automáticamente. Estas herramientas permiten a los usuarios identificar patrones y tendencias en los datos recopilados.

## Futuro y Escalabilidad
El proyecto está diseñado con una arquitectura modular y un enfoque en la extensibilidad, facilitando la incorporación de nuevos tipos de sensores, integraciones con sistemas externos o ajustes en las visualizaciones según las necesidades del usuario.

## Variables de Entorno
El proyecto requiere las siguientes variables de entorno en un archivo `.env`:

### Configuración Django
- `DJANGO_SECRET_KEY`: Clave secreta para Django (string alfanumérico largo) *(requerido)
- `DJANGO_DEBUG`: Estado de depuración (`True` o `False`) *(requerido)
- `DJANGO_ALLOWED_HOSTS`: Hosts permitidos (e.g., `localhost,example.com`) *(requerido)
- `DJANGO_TIMEZONE`: Zona horaria (e.g., `America/Santiago`) *(opcional, default: UTC)
- `DJANGO_STATIC_ROOT`: Ruta para archivos estáticos *(opcional, default: ./static)
- `DJANGO_MEDIA_ROOT`: Ruta para archivos multimedia *(opcional, default: ./media)
- `DJANGO_LOG_LEVEL`: Nivel de logging *(opcional, default: INFO)
- `DJANGO_ALLOWED_CORS`: Habilitar CORS *(opcional, default: false)
- `DJANGO_DEFAULT_LANGUAGE_CODE`: Código de idioma predeterminado *(opcional, default: en-us)

### Configuración Base de Datos
- `DB_ENGINE`: Motor de base de datos *(opcional, default: django.db.backends.sqlite3)
- `DB_NAME`: Nombre de la base de datos *(requerido)
- `DB_USER`: Usuario de la base de datos *(requerido si no es SQLite)
- `DB_PASSWORD`: Contraseña de la base de datos *(requerido si no es SQLite)
- `DB_HOST`: Host de la base de datos *(requerido si no es SQLite)
- `DB_PORT`: Puerto de la base de datos *(opcional, default: 5432 para PostgreSQL)

### Configuración DRF y CORS
- `DRF_DEFAULT_THROTTLE_RATES`: Límites de frecuencia de API *(opcional)
- `DRF_DEFAULT_PAGE_SIZE`: Tamaño de página predeterminado *(opcional, default: 10)
- `CORS_ALLOWED_ORIGINS`: Orígenes permitidos para CORS *(requerido si DJANGO_ALLOWED_CORS=true)

### Configuración del Monitor
- `MAX_DATA_MINUTES`: Ventana de tiempo máxima para consultas de sensores *(opcional, default: 5)
- `MAX_PLOT_RECORDS`: Número máximo de registros para gráficos *(opcional, default: 1000)

Para comenzar, copia el archivo `.env.example` a `.env` y ajusta los valores según tu entorno.
