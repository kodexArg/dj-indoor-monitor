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

## API RESTful

### Endpoints Principales

#### Datos de Sensores
- `GET /api/sensor-data/`: Obtiene registros de sensores
- `POST /api/sensor-data/`: Envía nuevos datos de sensores
- `GET /api/sensor-data/timeframed/`: Obtiene datos agregados por ventana de tiempo

### Timeframed API
El endpoint `/api/sensor-data/timeframed/` es especialmente útil para obtener datos agregados. Acepta los siguientes parámetros:

- `timeframe`: Ventana de tiempo para agregación
  - Valores válidos: '5s', '1T', '30T', '1h', '4h', '1D'
  - Default: '5s' (5 segundos)
- `window_minutes`: Período total a consultar en minutos
  - Default: 5 minutos
- `metric`: Métrica a consultar
  - 't': temperatura
  - 'h': humedad
  - Default: ambas

Ejemplo:
```
GET /api/sensor-data/timeframed/?timeframe=30T&window_minutes=120&metric=t
```

### Filtros Disponibles
La API soporta varios filtros para consultas específicas:

- `sensor_id`: Filtrar por ID de sensor
- `timestamp__gte`: Registros desde fecha
- `timestamp__lte`: Registros hasta fecha
- `t__gte`: Temperatura mayor o igual
- `h__gte`: Humedad mayor o igual

Ejemplo con filtros:
```
GET /api/sensor-data/?sensor_id=rpi-001&t__gte=25&timestamp__gte=2024-01-01
```

## Sistema de Visualización

### Gráficos Disponibles

1. **Overview**
   - Gráfico principal con datos en tiempo real
   - Soporte para diferentes timeframes
   - Cambio dinámico entre temperatura y humedad

2. **Sensores**
   - Vista individual por sensor
   - Gráficos de 4 horas para los últimos 4 días
   - Comparativa de temperatura y humedad

3. **VPD (Vapor Pressure Deficit)**
   - Visualización especializada para VPD
   - En desarrollo

### Interactividad HTMX
Los gráficos utilizan HTMX para:
- Actualizaciones en tiempo real
- Cambios de timeframe sin recarga
- Cambios entre métricas
- Indicadores de carga

### Integración API-Gráficos
Los gráficos consumen la API timeframed para:
- Optimizar la cantidad de datos mostrados
- Mantener la responsividad
- Permitir diferentes niveles de agregación

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


## Instalación
No se explican aquí todos los escenarios sino un caso típico, utilizando el mismo docker provisto; pero el sistema no tiene ninguna particularidad y cualquier instalación (con o sin virtual environment) en la que estén instalados los requirements (`requirements.txt`) servirá. También soporta cualquier base de datos.

Recuerda antes instalar dependencias si las necesitas. Por ejemplo en debian/ubuntu:
```
sudo apt update
sudo apt update
sudo apt install python3-dev build-essential libpq-dev

```

En un caso típico, este sistema incluye una base de datos postgrsql en docker, y el yaml está disponible en `/docker/docker-compose.yaml` para ejecutar directamente con `docker compose up -d`.

Para inicializar la base de datos de docker, ejecutar `docker exec -it postgres_db psql -U kodex_user -d dj_db` (por supuesto que puedes cambiar el usuario en .env). Finalmente crea la base de datos con `CREATE DATABASE dj_db;`

Lulego inicializa la DDBB con `python manage.py makemigrations && python manage.py migrate`


Para comenzar, copia el archivo `.env.example` a `.env` y ajusta los valores según tu entorno.
