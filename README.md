# dj-indoor-monitor

⚠️ **PROYECTO EN CONSTRUCCIÓN** ⚠️

Este proyecto se encuentra actualmente en desarrollo y **NO ES FUNCIONAL**. 

## Estado Actual y Próximos Pasos
El próximo objetivo es lograr la funcionalidad básica tanto en entorno de desarrollo como en producción:

### Desarrollo
```bash
python manage.py runserver
```

### Producción
```bash
cd docker && docker compose up
```

Una vez alcanzado este hito, se continuará con la implementación de las funcionalidades descritas a continuación.

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
- **Django 5.1+** como framework principal para el backend y manejo de vistas
- **Django REST Framework (DRF) 3.15+** para la API RESTful
- **Plotly 5.24+** para visualización de datos en gráficos interactivos
- **HTMX 1.21+** para actualizaciones dinámicas del frontend
- **Pandas 2.2+** para procesamiento y análisis de datos
- **Loguru** para logging avanzado
- **Pytest** con cobertura de tests
- **Uvicorn** como servidor ASGI
- **PostgreSQL** con psycopg2 para la base de datos
- **Python-dotenv** para manejo de variables de entorno
- **Gunicorn** como servidor WSGI de producción

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
El proyecto utiliza PostgreSQL con TimescaleDB como motor de base de datos, aprovechando sus capacidades para series temporales. La configuración se realiza a través del contenedor Docker proporcionado.

## Despliegue

### Requisitos
- Docker Engine 24.0+
- Docker Compose v2.0+
- ~2GB RAM mínimo recomendado
- 1GB espacio en disco mínimo

### Estructura Docker
El sistema se despliega mediante tres contenedores:
1. **webapp**: Aplicación Django con Gunicorn
2. **db**: TimescaleDB (PostgreSQL 14)
3. **nginx**: Servidor web y proxy inverso

### Proceso de Despliegue
1. Clonar el repositorio:
```bash
git clone https://github.com/usuario/dj-indoor-monitor.git
cd dj-indoor-monitor
```

2. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con los valores apropiados
```

3. Iniciar servicios:
```bash
docker compose -f docker/docker-compose.yml up -d
```

4. Verificar estado:
```bash
docker compose -f docker/docker-compose.yml ps
```

### Mantenimiento
- **Logs**: `docker compose -f docker/docker-compose.yml logs -f [servicio]`
- **Reinicio**: `docker compose -f docker/docker-compose.yml restart [servicio]`
- **Actualización**: 
```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up -d
```

### Backup de Datos
El volumen `postgres_data` persiste los datos. Para backup:
```bash
docker exec db pg_dump -U kodex_user dj_db > backup.sql
```

## Variables de Entorno
El proyecto requiere las siguientes variables de entorno en un archivo `.env`:

### Configuración Django
- `DJANGO_SECRET_KEY`: Clave secreta para Django *(requerido)*
- `DJANGO_DEBUG`: Estado de depuración (`True` o `False`) *(requerido)*
- `DJANGO_ALLOWED_HOSTS`: Hosts permitidos *(requerido)*
- `DJANGO_TIMEZONE`: Zona horaria (e.g., `America/Argentina/Buenos_Aires`) *(opcional, default: UTC)*
- `DJANGO_LOG_LEVEL`: Nivel de logging *(opcional, default: INFO)*
- `DJANGO_ALLOWED_CORS`: Habilitar CORS *(opcional, default: false)*
- `DJANGO_DEFAULT_LANGUAGE_CODE`: Código de idioma predeterminado (e.g., `es-ar`) *(opcional, default: en-us)*

### Configuración Base de Datos
- `DB_ENGINE`: Motor de base de datos (e.g., `django.db.backends.postgresql`) *(requerido)*
- `DB_NAME`: Nombre de la base de datos *(requerido)*
- `DB_USER`: Usuario de la base de datos *(requerido)*
- `DB_PASSWORD`: Contraseña de la base de datos *(requerido)*
- `DB_HOST`: Host de la base de datos *(requerido)*
- `DB_PORT`: Puerto de la base de datos *(requerido)*
- `DB_LOCAL`: Host local para conexiones locales *(opcional)*

### Configuración DRF
- `DRF_DEFAULT_THROTTLE_RATES`: Límites de frecuencia de API (e.g., `anon:1000/day`) *(opcional)*
- `DRF_DEFAULT_PAGE_SIZE`: Tamaño de página predeterminado *(opcional, default: 20)*

### Configuración del Monitor
- `MAX_DATA_MINUTES`: Ventana de tiempo máxima para consultas de sensores *(opcional, default: 5)*
- `MAX_PLOT_RECORDS`: Número máximo de registros para gráficos *(opcional, default: 300)*


Firmo en acuerdo con lo escrito por la ai.