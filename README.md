# dj-indoor-monitor

## 1. Sobre el sistema

Sistema de monitoreo de sensores para cultivos indoor mediante dispositivos Raspberry Pi.

**Actualmente el sitio web se encuentra en mantenimiento y la visualización de datos ha sido suspendida temporalmente.** La API REST sigue operativa para la recolección y consulta de datos.

### Tecnologías Empleadas
- **Framework**: Django, DRF
- **Base de Datos**: PostgreSQL, TimescaleDB
- **Infraestructura**: Docker, Gunicorn, Nginx
- **Testing**: Pytest

## 2. Funcionamiento

### Arquitectura
Infraestructura basada en contenedores:
- **webapp**: Django + Gunicorn
- **db**: TimescaleDB (PostgreSQL)
- **nginx**: Reverse proxy
Esta misma infraestructura funciona en entorno local, usando el mismo docker db (`python manage.py runserver`)

### Flujo de Datos
1. Sensores -> API
2. Almacenamiento -> TimescaleDB (PostreSQL)

## 3. API

La API está basada en Django REST Framework y expone los siguientes endpoints:

### 3.1 Data-Point API

Base endpoint para operaciones CRUD estándar:
```bash
/api/data-point/
```
Este endpoint permite crear, leer, actualizar y eliminar (`POST`, `GET`, `PUT`/`PATCH`, `DELETE`) registros de DataPoint.

#### Acciones Personalizadas

1.  **Últimas lecturas por sensor (`/latest/`)**
    ```bash
    GET /api/data-point/latest/
    ```
    Obtiene el último registro para cada sensor, opcionalmente filtrado por un rango de fechas y/o sensores específicos.

    *Parámetros de consulta (opcionales):*
    - `start_date`: Fecha de inicio (ISO 8601) para el rango de búsqueda.
    - `end_date`: Fecha de fin (ISO 8601) para el rango de búsqueda.
    - `sensors`: Lista de IDs de sensor (separados por coma o como parámetro múltiple, ej: `sensors=sensor1&sensors=sensor2`).
    - `metadata`: Booleano (`true`/`false`). Si es `true`, incluye metadatos sobre la consulta.
    - `include_room`: Booleano (`true`/`false`). Si es `true`, incluye el nombre del `room` asociado a cada sensor.

2.  **Datos agregados por intervalos (`/timeframed/`)**
    ```bash
    GET /api/data-point/timeframed/
    GET /timeframed/ # Atajo disponible
    ```
    Obtiene registros agregados según un intervalo de tiempo (`timeframe`) especificado.

    *Parámetros de consulta:*
    - `timeframe`: Intervalo de agregación (ej: `5S`, `1T` para 1 minuto, `30T`, `1H`, `4H`, `1D`). **Requerido.**
    - `start_date`: Fecha de inicio (ISO 8601) para la agregación.
    - `end_date`: Fecha de fin (ISO 8601) para la agregación.
    - `sensors`: Lista de IDs de sensor (separados por coma o como parámetro múltiple).
    - `metrics`: Lista de métricas específicas a incluir (ej: `t,h,s,l`).
    - `aggregations`: Booleano (`true`/`false`).
        - Si es `false` (valor por defecto): Devuelve solo el valor promedio (`mean`) para cada métrica.
        - Si es `true`: Devuelve múltiples agregaciones: `min`, `max`, `mean`, `first` (primer valor del intervalo), `last` (último valor del intervalo).
    - `metadata`: Booleano (`true`/`false`). Si es `true`, incluye metadatos sobre la consulta (tiempos, rango de fechas, timeframe).
    - `include_room`: Booleano (`true`/`false`). Si es `true`, incluye el nombre del `room` asociado a cada sensor en los datos agrupados.

#### Parámetros de Consulta Comunes
Los siguientes parámetros pueden ser aplicados a la mayoría de los endpoints de listado (`/api/data-point/`, `/latest/`, `/timeframed/`) para filtrar los resultados:
- `start_date`: Filtra los registros desde esta fecha/hora (formato ISO 8601).
- `end_date`: Filtra los registros hasta esta fecha/hora (formato ISO 8601).
- `sensors`: Filtra por una lista de IDs de sensor (ej: `sensor1,sensor2` o `sensors=sensor1&sensors=sensor2`).
- `metric__range_name`: Filtra por un rango numérico para una métrica específica. `range_name` puede ser `gt` (mayor que), `gte` (mayor o igual que), `lt` (menor que), `lte` (menor o igual que). Ejemplo: `metric__t__gte=20&metric__t__lte=25` para temperatura entre 20 y 25.
- `metadata`: (`true`/`false`) Cuando se establece a `true` en endpoints que lo soportan (`/latest/`, `/timeframed/`), añade un bloque `metadata` a la respuesta con información sobre la ejecución de la consulta.
- `include_room`: (`true`/`false`) Cuando se establece a `true` en endpoints que lo soportan (`/latest/`, `/timeframed/`), el campo `room` (nombre del espacio) se añade a cada registro de datos del sensor.

### Operaciones CRUD

```bash
GET /api/data-point/
```
```json
{
    "results": [{"timestamp": "2024-01-15T14:30:00Z", "sensor": "rpi-001", "metric": "t", "value": 24.5}],
    "count": 1
}
```

```bash
POST /api/data-point/
{"sensor": "rpi-001", "metric": "t", "value": 24.5}
```

### Agregación Temporal

El endpoint `/timeframed/` implementa agregaciones. Por ejemplo para obtener los datos agrupados cada 30 minutos, desde 2025:

```bash
GET /api/data-point/timeframed/?timeframe=30T&start_date=2025-01-01
```

> **Nota**: Los timeframes se especifican utilizando un número seguido de una unidad de tiempo. Por ejemplo, `30T` se refiere a 30 minutos, `1h` a 1 hora, `4h` a 4 horas, y `1D` a 1 día. Los valores válidos para timeframe se definen en la configuración del sistema y usualmente incluyen `5S`, `1T`, `5T`, `15T`, `30T`, `1H`, `2H`, `4H`, `12H`, `1D`.

Parámetros (para `/timeframed/`):
- `timeframe`: Intervalo de agregación. (Ver lista y descripción detallada arriba).
- `start_date`: Fecha de inicio para la agregación.
- `end_date`: Fecha de fin para la agregación.
- `sensors`: Lista de IDs de sensor (opcional, separados por comas o como parámetro múltiple).
- `metrics`: Lista de métricas específicas a incluir (opcional, ej: `t,h,s,l`).
- `aggregations`: Booleano. `false` (defecto) para solo `mean`, `true` para `min, max, mean, first, last`.
- `metadata`: Booleano (`true`/`false`). Incluir metadatos de la consulta.
- `include_room`: Booleano (`true`/`false`). Incluir el nombre del `room`.

Respuesta (sin aggregations, `aggregations=false`):
```json
{
    "data": [{
        "timestamp": "2024-01-15T14:30:00Z",
        "sensor": "rpi-001",
        "metric": "t",
        "value": 24.5
    }],
    "metadata": {
        "start_time": "2024-01-15T14:00:00Z",
        "elapsed_time": 0.123,
        "start_date": "2025-01-01",
        "end_date": "2025-01-02",
        "timeframe": "30T"
    }
}
```

Respuesta (con aggregations):
```json
{
    "data": [{
        "timestamp": "2024-01-15T14:30:00Z",
        "sensor": "rpi-001",
        "metric": "t",
        "value": {
            "mean": 24.5,
            "min": 23.1,
            "max": 25.8,
            "first": 23.5,
            "last": 25.5
        }
    }],
    "metadata": {
        "start_time": "2024-01-15T14:00:00Z",
        "elapsed_time": 0.123,
        "start_date": "2025-01-01",
        "end_date": "2025-01-02",
        "timeframe": "30T"
    }
}
```

### 3.2 RPI Sensor Service

El servicio de sensores RPI se encarga de la recolección de datos de los sensores y su envío a la API. Está implementado en Python y se ejecuta en los dispositivos Raspberry Pi.

#### Instalación

1. Clonar el repositorio en el Raspberry Pi:
```bash
git clone https://github.com/usuario/rpi-sensor-service.git
cd rpi-sensor-service
```

2. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar las variables de entorno:
```env
# API
API_URL=http://localhost:8000/api/data-point/
API_KEY=your_api_key

# Sensor
SENSOR_ID=rpi-001
```

4. Ejecutar el servicio:
```bash
python sensor_service.py
```

## 4. Instalación

### Requisitos
- Docker + Docker Compose

### Configuración
1. Clonar repositorio
```bash
git clone https://github.com/usuario/dj-indoor-monitor.git
cd dj-indoor-monitor
```

2. Variables de entorno:
```env
# Django
DJANGO_SECRET_KEY=key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=nombre_db
DB_USER=usuario_db
DB_PASSWORD=pass_db
DB_HOST=db
DB_PORT=5432

# API
DRF_DEFAULT_THROTTLE_RATES=anon:1000/day
DRF_DEFAULT_PAGE_SIZE=50

# Monitor
IGNORE_SENSORS=sensor1,sensor2

# Locale
DJANGO_TIMEZONE=America/Argentina/Buenos_Aires
DJANGO_DEFAULT_LANGUAGE_CODE=es-ar
```

3. Despliegue:
```bash
docker compose up -d
```

## 5. Colaboración

Contribuciones mediante Pull Request.

### Contribuir
1. Haz un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus cambios y haz commit (`git commit -am 'Agrega nueva funcionalidad'`).
4. Sube tus cambios a la rama (`