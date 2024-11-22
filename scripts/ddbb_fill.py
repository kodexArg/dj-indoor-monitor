"""
Script para llenar la base de datos con datos fake de sensores.

Uso:
    python ddbb_fill.py --start-date YYYY-MM-DDTHH:MM:SS

Ejemplos:

    Ejecutar el script con solo el parámetro obligatorio:
        python ddbb_fill.py --start-date 2023-10-01T00:00:00

    Especificar un intervalo de 60 segundos entre datos:
        python ddbb_fill.py --start-date 2023-10-01T00:00:00 --seconds 60

    Simular 5 sensores desde una fecha de inicio hasta una fecha de fin:
        python ddbb_fill.py --start-date 2023-10-01T00:00:00 --end-date 2023-10-02T00:00:00 --sensors 5

    Usar una fecha de inicio de hace 7 días:
        python ddbb_fill.py --start-date $(date -d "-7 days" '+%Y-%m-%dT%H:%M:%S')

Parámetros obligatorios:
    --start-date: Fecha y hora de inicio en formato ISO8601 para los datos generados.
                  Ejemplo: --start-date 2023-10-01T00:00:00

Parámetros opcionales:
    --end-date:   Fecha y hora de fin en formato ISO8601. Por defecto es la fecha y hora actual.
                  Ejemplo: --end-date 2023-10-02T00:00:00
    --seconds:    Intervalo en segundos entre cada dato generado. Por defecto es 30 segundos.
                  Ejemplo: --seconds 60
    --sensors:    Número de sensores a simular. Por defecto son 3 sensores.
                  Ejemplo: --sensors 5

El script generará datos de sensores falsos desde la fecha de inicio hasta la fecha de fin,
incrementando el tiempo por el intervalo especificado, y cargará los datos en la base de datos
sin ninguna demora.
"""

# Standard library imports
import sys
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Third party imports
import sqlite3
from dateutil import parser as date_parser
from loguru import logger

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>",
    colorize=True,
    level="INFO"
)

# Parse arguments
parser = argparse.ArgumentParser(description="Script para llenar la base de datos con datos fake")
parser.add_argument("--start-date", required=True, help="Fecha de inicio en formato ISO8601")
parser.add_argument("--end-date", help="Fecha de fin en formato ISO8601 (opcional)")
parser.add_argument("--seconds", type=int, default=30, help="Intervalo entre datos en segundos")
parser.add_argument("--sensors", type=int, default=3, help="Número de sensores simulados")

if len(sys.argv) == 1:
    print(__doc__)
    sys.exit(1)

args = parser.parse_args()

# Constants
DB_PATH = Path(__file__).parent.parent / "db.sqlite3"
BATCH_SIZE = 1000  # Número de registros por transacción
interval = args.seconds
start_date = date_parser.parse(args.start_date)
# Asegurar que end_date no supere la fecha actual
now = datetime.now()
end_date = min(
    date_parser.parse(args.end_date) if args.end_date else now,
    now
)
SENSORS = [f"simu-sensor-{i:02d}" for i in range(1, args.sensors + 1)]

# Track last values for each sensor
sensor_states = {}

def get_initial_state(sensor_name):
    if sensor_name not in sensor_states:
        sensor_states[sensor_name] = {
            'temperature': random.uniform(20.0, 25.0),  # Start with reasonable values
            'humidity': random.uniform(40.0, 60.0)
        }
    return sensor_states[sensor_name]

def generate_next_value(current_value, max_change, is_temperature=False, timestamp=None):
    if is_temperature and timestamp:
        hour = timestamp.hour
        is_night = 20 <= hour or hour < 6
        
        # Extreme temperature cases (highest priority)
        if current_value >= 35.0:
            change = random.uniform(-max_change * 2, 0)  # Strong cooling
        elif current_value <= 15.0:
            change = random.uniform(0, max_change * 2)  # Strong warming
        # Night temperature logic
        elif is_night:
            if current_value > 25.0:
                change = random.uniform(-max_change * 1.2, 0)  # Cool down
            elif current_value < 20.0:
                change = random.uniform(0, max_change)  # Warm up
            else:
                change = random.uniform(-max_change, max_change)  # Normal range
        # Day temperature logic
        else:
            if current_value > 30.0:
                change = random.uniform(-max_change, max_change)  # Normal range
            elif current_value < 25.0:
                change = random.uniform(0, max_change * 1.2)  # Warm up
            else:
                change = random.uniform(-max_change, max_change)  # Normal range
    else:
        change = random.uniform(-max_change, max_change)
    
    return current_value + change

def generate_temperature(sensor_name, timestamp):
    state = get_initial_state(sensor_name)
    new_temp = generate_next_value(
        state['temperature'],
        max_change=0.5,
        is_temperature=True,
        timestamp=timestamp
    )
    state['temperature'] = new_temp
    return round(new_temp, 1)

def generate_humidity(sensor_name):
    state = get_initial_state(sensor_name)
    new_humidity = generate_next_value(
        state['humidity'],
        max_change=1.0
    )
    # Keep humidity within bounds
    new_humidity = max(20.0, min(80.0, new_humidity))
    state['humidity'] = new_humidity
    return round(new_humidity, 1)

def insert_batch(conn, data_batch):
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO core_sensordata (timestamp, sensor, t, h) VALUES (?, ?, ?, ?)",
        data_batch
    )
    conn.commit()

def main():
    logger.info("Inicio del proceso para llenar la base de datos con datos fake.")
    current_time = start_date
    data_batch = []
    
    with sqlite3.connect(DB_PATH) as conn:
        while current_time <= end_date:
            for sensor_name in SENSORS:
                temperature = generate_temperature(sensor_name, current_time)
                humidity = generate_humidity(sensor_name)
                data_batch.append((
                    current_time.isoformat(),
                    sensor_name,
                    temperature,
                    humidity
                ))
                
                # Insertar cuando el lote está lleno
                if len(data_batch) >= BATCH_SIZE:
                    insert_batch(conn, data_batch)
                    logger.info(f"Insertados {BATCH_SIZE} registros hasta {current_time}")
                    data_batch = []
            
            current_time += timedelta(seconds=interval)
        
        # Insertar registros restantes
        if data_batch:
            insert_batch(conn, data_batch)
            logger.info(f"Insertados {len(data_batch)} registros finales")
    
    logger.info("Proceso completado.")

if __name__ == "__main__":
    main()
