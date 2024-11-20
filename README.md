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
