# Standard library imports
import sys
import time
import random
import threading
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sqlite3
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from threading import Event
# Third party imports
import requests
from loguru import logger
from dateutil import parser as date_parser

# Configurar logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>",
    colorize=True,
    level="INFO"
)

# Constantes Globales
DB_PATH = Path(__file__).parent.parent / "db.sqlite3"
BATCH_SIZE = 1000
TIMEZONE = ZoneInfo('America/Argentina/Buenos_Aires')
USE_LOCAL_TIME = True
ENDPOINT = "http://127.0.0.1:8000/api/sensor-data/"
DEFAULT_INTERVAL = 30
DEFAULT_SENSORS = 3
db_queue = Queue()
stop_event = Event()

def db_writer():
    """
    Thread worker that handles all database writes through a queue
    """
    conn = sqlite3.connect(DB_PATH)
    while not stop_event.is_set() or not db_queue.empty():
        try:
            batch = db_queue.get(timeout=1.0)
            insert_batch(conn, batch)
            db_queue.task_done()
        except Queue.Empty:
            continue
    conn.close()
    logger.info("Database writer thread finished")

# Argumentos de línea de comandos
parser = argparse.ArgumentParser(description="Script unificado para simular históricos y tiempo real de sensores")
parser.add_argument("--start-date", required=True, help="Fecha de inicio en formato ISO8601")
parser.add_argument("--end-date", help="Fecha de fin en formato ISO8601 (opcional)")
parser.add_argument("--seconds", type=int, default=DEFAULT_INTERVAL, help="Intervalo de captura en segundos")
parser.add_argument("--sensors", type=int, default=DEFAULT_SENSORS, help="Número de sensores simulados (mínimo 1)")
parser.add_argument("--delete-ddbb", action="store_true", help="Eliminar datos existentes en la base de datos antes de comenzar")
args = parser.parse_args()

# Validar argumentos
if args.sensors <= 0:
    logger.error("El número de sensores debe ser mayor que 0")
    sys.exit(1)

# Constantes derivadas de argumentos
interval = args.seconds

def process_dates(start_date_str, end_date_str=None):
    """
    Procesa y valida las fechas de inicio y fin.
    
    Args:
        start_date_str: Fecha de inicio en formato ISO8601
        end_date_str: Fecha de fin en formato ISO8601 (opcional)
    
    Returns:
        tuple: (start_date, end_date) con zonas horarias configuradas
        
    Raises:
        ValueError: Si las fechas no son válidas o si end_date < start_date
    """
    def ensure_timezone(dt):
        return dt.replace(tzinfo=TIMEZONE) if dt.tzinfo is None else dt

    try:
        start_date = ensure_timezone(date_parser.parse(start_date_str))
        now = ensure_timezone(datetime.now() if USE_LOCAL_TIME else datetime.utcnow())
        end_date = ensure_timezone(date_parser.parse(end_date_str) if end_date_str else now)

        if end_date < start_date:
            raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
            
        return start_date, end_date

    except Exception as e:
        logger.error(f"Error procesando fechas: {str(e)}")
        sys.exit(1)

# Procesar fechas
start_date, end_date = process_dates(args.start_date, args.end_date)
SENSORS = [f"simu-rpi-{i:02d}" for i in range(1, args.sensors + 1)]

# Eliminar datos de la base de datos si se indica
if args.delete_ddbb:
    def delete_all_data(db_path):
        """
        Elimina todos los datos de la base de datos.
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM core_sensordata")
            conn.commit()
            logger.info("Todos los datos de la tabla 'core_sensordata' han sido eliminados.")
        except sqlite3.Error as e:
            logger.error(f"Error al eliminar datos: {e}")
        finally:
            if conn:
                conn.close()

    confirmation = input("¿Está seguro de que desea eliminar todos los datos de la base de datos? (y/N): ")
    if confirmation.lower() == 'y':
        delete_all_data(DB_PATH)
    else:
        logger.info("Operación cancelada por el usuario.")
        sys.exit(0)

# Generación de datos
sensor_states = {}

def get_initial_state(sensor_name):
    """
    Obtiene o inicializa el estado del sensor.
    """
    if sensor_name not in sensor_states:
        sensor_states[sensor_name] = {
            'temperature': random.uniform(20.0, 25.0),
            'humidity': random.uniform(40.0, 60.0)
        }
    return sensor_states[sensor_name]

def generate_next_value(current_value, max_change, is_temperature=False, timestamp=None):
    """
    Genera el siguiente valor de temperatura o humedad.
    """
    if is_temperature and timestamp:
        hour = timestamp.hour
        is_night = 20 <= hour or hour < 6
        
        if current_value >= 35.0:
            change = random.uniform(-max_change * 2, 0) if random.random() < 0.67 else random.uniform(-max_change, max_change)
        elif current_value <= 15.0:
            change = random.uniform(0, max_change * 2) if random.random() < 0.67 else random.uniform(-max_change, max_change)
        elif is_night:
            if current_value > 25.0:
                change = random.uniform(-max_change * 1.2, 0)
            elif current_value < 20.0:
                change = random.uniform(0, max_change)
            else:
                change = random.uniform(-max_change, max_change)
        else:
            if current_value > 30.0:
                change = random.uniform(-max_change, max_change)
            elif current_value < 25.0:
                change = random.uniform(0, max_change * 1.2)
            else:
                change = random.uniform(-max_change, max_change)
    else:
        change = random.uniform(-max_change, max_change)
    
    return current_value + change

def generate_temperature(sensor_name, timestamp):
    """
    Genera un nuevo valor de temperatura para un sensor.
    La temperatura varía en función de la hora del día para simular las diferencias naturales.
    Durante el día, la temperatura tiende a subir, mientras que durante la noche, tiende a bajar.
    Esta variación ocurre cada vez que se genera un nuevo dato, aproximadamente cada 'interval' segundos.
    """
    state = get_initial_state(sensor_name)
    new_temp = generate_next_value(
        state['temperature'],
        max_change=0.25,
        is_temperature=True,
        timestamp=timestamp
    )
    state['temperature'] = new_temp
    return round(new_temp, 1)

def generate_humidity(sensor_name):
    """
    Genera un nuevo valor de humedad para un sensor.
    La humedad varía de manera más aleatoria, pero siempre se mantiene dentro de un rango razonable (20% - 80%).
    Esta variación ocurre cada vez que se genera un nuevo dato, aproximadamente cada 'interval' segundos.
    """
    state = get_initial_state(sensor_name)
    new_humidity = generate_next_value(
        state['humidity'],
        max_change=0.5
    )
    new_humidity = max(20.0, min(80.0, new_humidity))
    state['humidity'] = new_humidity
    return round(new_humidity, 1)

def insert_batch(conn, data_batch):
    """
    Inserta un lote de datos en la base de datos.
    """
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO core_sensordata (timestamp, sensor, t, h) VALUES (?, ?, ?, ?)",
        data_batch
    )
    conn.commit()

class HistoricalSensorSimulator(threading.Thread):
    """
    Simulador de sensor histórico que genera datos históricos para un sensor.
    """
    def __init__(self, sensor_name):
        threading.Thread.__init__(self)
        self.sensor_name = sensor_name
        self.current_time = start_date.astimezone(TIMEZONE) if USE_LOCAL_TIME else start_date
        self.running = True
        self.data_batch = []

    def run(self):
        """
        Genera datos históricos para el sensor.
        """
        logger.info(f"Inicio del proceso de llenado histórico para {self.sensor_name}")
        while self.current_time <= end_date:
            temperature = generate_temperature(self.sensor_name, self.current_time)
            humidity = generate_humidity(self.sensor_name)
            self.data_batch.append((
                self.current_time.isoformat(),
                self.sensor_name,
                temperature,
                humidity
            ))
            if len(self.data_batch) >= BATCH_SIZE:
                db_queue.put(self.data_batch)
                logger.info(f"Encolados {BATCH_SIZE} registros hasta {self.current_time} para {self.sensor_name}")
                self.data_batch = []
            
            self.current_time += timedelta(seconds=interval)
            time.sleep(0.001)  # Minimal sleep to prevent CPU hogging
        
        if self.data_batch:
            db_queue.put(self.data_batch)
            logger.info(f"Encolados {len(self.data_batch)} registros finales para {self.sensor_name}")
        
        logger.info(f"Proceso de datos históricos completado para {self.sensor_name}")

class RealTimeSensorSimulator(threading.Thread):
    """
    Simulador de sensor en tiempo real que envía datos a un endpoint.
    """
    def __init__(self, sensor_name):
        threading.Thread.__init__(self)
        self.sensor_name = sensor_name
        self.running = True
        self.temperature = 22.0
        self.humidity = 60.0
        self.prev_temperature = self.temperature
        self.prev_humidity = self.humidity
        self.error_shown = False

    def run(self):
        """
        Genera y envía datos en tiempo real para el sensor.
        """
        while self.running:
            self.update_temperature()
            self.update_humidity()
            if not self.send_data():
                if not self.error_shown:
                    logger.error(f"{self.sensor_name}: API no accesible, intentando reconexión cada {interval} segundos...")
                    self.error_shown = True
                time.sleep(interval)
                continue
            
            if self.error_shown:
                logger.info(f"{self.sensor_name}: API accesible nuevamente")
                self.error_shown = False
                
            latency = random.uniform(0, 0.5)  # Añadir retardo aleatorio de hasta medio segundo
            local_now = datetime.now(TIMEZONE) if USE_LOCAL_TIME else datetime.utcnow()
            logger.info(f"{self.sensor_name}: {local_now.strftime('%H:%M:%S')} (+{latency:.3f}s) | "
                     f"T:{self.prev_temperature:.1f}°->{self.temperature:.1f}° | "
                     f"H:{self.prev_humidity:.1f}%->{self.humidity:.1f}%")
            time.sleep(interval + latency)

    def update_temperature(self):
        self.prev_temperature = self.temperature
        if self.temperature >= 35.0:
            variation = round(random.uniform(-0.5, 0.25), 1) if random.random() < 0.67 else round(random.uniform(-0.25, 0.25), 1)
        elif self.temperature <= 15.0:
            variation = round(random.uniform(-0.25, 0.5), 1) if random.random() < 0.67 else round(random.uniform(-0.25, 0.25), 1)
        else:
            variation = round(random.uniform(-0.25, 0.25), 1)
        self.temperature += variation
        self.temperature = round(min(35.0, max(15.0, self.temperature)), 1)

    def update_humidity(self):
        self.prev_humidity = self.humidity
        if self.humidity >= 80.0:
            variation = round(random.uniform(-2.0, 1.0), 1) if random.random() < 0.67 else round(random.uniform(-1.0, 1.0), 1)
        elif self.humidity <= 20.0:
            variation = round(random.uniform(-1.0, 2.0), 1) if random.random() < 0.67 else round(random.uniform(-1.0, 1.0), 1)
        else:
            variation = round(random.uniform(-1.0, 1.0), 1)
        self.humidity += variation
        self.humidity = round(min(80.0, max(20.0, self.humidity)), 1)

    def send_data(self):
        utc_now = datetime.now(TIMEZONE) if USE_LOCAL_TIME else datetime.utcnow()
        data = {
            "timestamp": utc_now.isoformat(),
            "sensor": self.sensor_name,
            "t": self.temperature,
            "h": self.humidity
        }
        try:
            response = requests.post(ENDPOINT, json=data)
            if response.status_code != 201:
                logger.error(f"{self.sensor_name}: Endpoint no accesible, cerrando el script.")
                sys.exit(1)
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.sensor_name}: Error de conexión ({e}), cerrando el script.")
            sys.exit(1)
        return True

    def get_latency(self):
        return random.randint(1, 1000) / 1000

# Inicio del script
if __name__ == "__main__":
    # Start database writer thread
    db_writer_thread = threading.Thread(target=db_writer)
    db_writer_thread.daemon = True
    db_writer_thread.start()

    # Start historical simulators without blocking
    historical_simulators = []
    for sensor in SENSORS:
        historical_simulator = HistoricalSensorSimulator(sensor)
        historical_simulator.daemon = True
        historical_simulator.start()
        historical_simulators.append(historical_simulator)

    # Start real-time simulators immediately
    simulators = []
    for sensor in SENSORS:
        simulator = RealTimeSensorSimulator(sensor)
        simulator.daemon = True
        simulator.start()
        simulators.append(simulator)

    logger.info(f"Intervalo de actualización configurado a {interval} segundos")
    logger.info(f"Simulando {len(SENSORS)} sensores en tiempo real")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        logger.info("Finalizando procesos...")
        # Wait for queue to empty
        db_queue.join()
        sys.exit(0)
