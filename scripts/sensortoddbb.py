from loguru import logger
import asyncio
import aiohttp
import argparse
from datetime import datetime, timedelta
import random
import sqlite3
import sys

# Configure logger to remove timestamp and function name
logger.remove()
logger.add(sys.stderr, format="{level}: {message}")

# función que inserta valores en http://127.0.0.0:8000/api/sensor-data/ de core.views.SensorDataViewSet

URL = "http://127.0.0.1:8000/api/sensor-data/write_values/"
HEADERS = {'Content-Type': 'application/json'}

async def insertar_valores(sensor_data):
    sensor_data['t'] = round(sensor_data['t'], 1)
    sensor_data['h'] = round(sensor_data['h'], 1)
    sensor_data['timestamp'] = sensor_data['timestamp'].split('.')[0]  # Remove milliseconds
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, json=sensor_data, headers=HEADERS) as response:
            if response.status == 201:
                logger.info(f"time={sensor_data['timestamp']} (sensor={sensor_data['sensor']}, h={sensor_data['h']}%, t={sensor_data['t']}°C)")
            else:
                logger.warning(f"Error al insertar datos: {response.status}")
                exit(1)

def generate_metric_value(metric: str, last_value: float = None, timestamp: datetime = None) -> float:
    if metric == 't':
        max_change = 1.0
        is_temperature = True
    elif metric == 'h':
        max_change = 2.0
        is_temperature = False
    else:
        raise ValueError("Metric must be 't' for temperature or 'h' for humidity")
    
    if last_value is None:
        last_value = 24.0 if metric == 't' else 60.0
    
    if is_temperature and timestamp:
        hour = timestamp.hour
        is_night = 20 <= hour or hour < 6
        
        if last_value >= 35.0:
            change = random.uniform(-max_change * 2, 0) if random.random() < 0.67 else random.uniform(-max_change, max_change)
        elif last_value <= 15.0:
            change = random.uniform(0, max_change * 2) if random.random() < 0.67 else random.uniform(-max_change, max_change)
        elif is_night:
            if last_value > 25.0:
                change = random.uniform(-max_change * 1.2, 0)
            elif last_value < 20.0:
                change = random.uniform(0, max_change)
            else:
                change = random.uniform(-max_change, max_change)
        else:
            if last_value > 30.0:
                change = random.uniform(-max_change, max_change)
            elif last_value < 25.0:
                change = random.uniform(0, max_change * 1.2)
            else:
                change = random.uniform(-max_change, max_change)
    else:
        change = random.uniform(-max_change, max_change)
    
    return last_value + change

def calculate_next_timestamp(previous_timestamp: datetime, seconds: int) -> datetime:
    latency = random.uniform(0, 0.02) * seconds
    return previous_timestamp + timedelta(seconds=seconds + latency)

def delete_all_data(db_path: str) -> None:
    conn: sqlite3.Connection = None
    try:
        conn = sqlite3.connect(db_path)
        cursor: sqlite3.Cursor = conn.cursor()
        cursor.execute("DELETE FROM core_sensordata") 
        conn.commit()
        logger.info("Datos eliminados de 'core_sensordata'.")
    except sqlite3.Error as e:
        logger.error(f"Error al eliminar datos: {e}")
    finally:
        if conn:
            conn.close()

def prepare_arguments():
    parser = argparse.ArgumentParser(description="Insert sensor data into the database.")
    parser.add_argument('--sensor', type=str, required=True, help='Name of the sensor to add')
    parser.add_argument('--seconds', type=int, default=5, help='Seconds between timestamps (default: 5)')
    parser.add_argument('--start-date', type=str, default=(datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S'), help='Start date (default: 48 hours ago)')
    parser.add_argument('--end-date', type=str, default=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'), help='End date (default: 1 hour in the future)')
    parser.add_argument('--delete', action='store_true', help='Delete all data before inserting new data')
    
    return parser.parse_args()

async def loop_write_values(sensor: str, start_date: datetime, seconds: int, stop_time: datetime = None):
    current_timestamp = start_date
    last_temperature = 24.0
    last_humidity = 60.0

    tasks = []

    while True:
        temperature = generate_metric_value('t', last_temperature, current_timestamp)
        humidity = generate_metric_value('h', last_humidity, current_timestamp)
        
        sensor_data = {
            'timestamp': current_timestamp.isoformat().split('.')[0],  # Remove milliseconds
            'sensor': sensor,
            't': round(temperature, 1),
            'h': round(humidity, 1)
        }
        
        tasks.append(insertar_valores(sensor_data))
        
        last_temperature = temperature
        last_humidity = humidity
        current_timestamp = calculate_next_timestamp(current_timestamp, seconds)
        
        if len(tasks) >= 10:  # Adjust the batch size as needed
            await asyncio.gather(*tasks)
            tasks = []

        if stop_time and current_timestamp >= stop_time:
            break

        # Remove or reduce the sleep time to speed up the loop
        # await asyncio.sleep(seconds)

    if tasks:
        await asyncio.gather(*tasks)

async def main():
    args = prepare_arguments()
    
    if args.delete:
        delete_all_data('../db.sqlite3')
    
    sensor = args.sensor
    seconds = args.seconds
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d %H:%M:%S')
    
    try:
        await loop_write_values(sensor, start_date, seconds, stop_time=end_date)
    except asyncio.CancelledError:
        logger.warning("Proceso interrumpido por el usuario (Ctrl+C). Limpiando y saliendo...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Proceso interrumpido por el usuario (Ctrl+C). Limpiando y saliendo...")