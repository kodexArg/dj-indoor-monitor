
# Sensor Data API

API para gestionar datos de sensores de temperatura y humedad desde Raspberry Pi.

## Endpoints

### GET /api/sensor-data/
### GET /api/sensor-data/<raspberry_pi_id>/

Obtiene datos de sensores filtrados por tiempo y opcionalmente por ID de Raspberry Pi.

**Parámetros URL:**
- `raspberry_pi_id` (opcional): Identificador del Raspberry Pi
- `seconds` (opcional): Ventana de tiempo en segundos (default: 3600)

**Respuestas:**
- `200 OK`: Lista de lecturas de sensores
- `500 Error`: Error del servidor con detalles

### POST /api/sensor-data/

Almacena nuevas lecturas de sensores.

**Formato JSON esperado:**