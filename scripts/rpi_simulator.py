# Standard library imports
import sys
import time
import random
import threading
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo  # Add this import

# Third party imports
import requests
from loguru import logger

# Configure logger
logger.remove()  
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    colorize=True,
    level="INFO"
)

# Parse arguments
parser = argparse.ArgumentParser(description="Simulador de Sensores")
parser.add_argument("--seconds", type=int, default=30, help="Intervalo de actualización en segundos")
parser.add_argument("--sensors", type=int, default=3, help="Número de sensores simulados")
args = parser.parse_args()

# Constants
endpoint = "http://127.0.0.1:8000/api/sensor-data/"
interval = args.seconds
SENSORS = [f"simu-sensor-{i:02d}" for i in range(1, args.sensors + 1)]
TIMEZONE = ZoneInfo('America/Argentina/Buenos_Aires') 

class SensorSimulator(threading.Thread):
    def __init__(self, sensor_name):
        threading.Thread.__init__(self)
        self.sensor_name = sensor_name
        self.running = True
        self.temperature = 22.0
        self.humidity = 60.0
        self.prev_temperature = self.temperature
        self.prev_humidity = self.humidity
        self.error_shown = False  # Nueva variable para controlar el mensaje de error

    def update_temperature(self):
        self.prev_temperature = self.temperature
        if random.random() < 0.05:  # 5% de probabilidad
            variation = round(random.uniform(-0.5, 0.5), 1)
            self.temperature += variation
            self.temperature = round(min(35.0, max(15.0, self.temperature)), 1)

    def update_humidity(self):
        self.prev_humidity = self.humidity
        if random.random() < 0.05:  # 5% de probabilidad
            variation = round(random.uniform(-2.0, 2.0), 1)
            self.humidity += variation
            self.humidity = round(min(80.0, max(20.0, self.humidity)), 1)

    def send_data(self):
        # Usar UTC para el API
        utc_now = datetime.now().astimezone()  # Esto da UTC
        data = {
            "timestamp": utc_now.isoformat(),
            "sensor": self.sensor_name,
            "t": self.temperature,
            "h": self.humidity
        }
        try:
            response = requests.post(endpoint, json=data)
            if response.status_code != 201:
                return False
        except requests.exceptions.RequestException:
            return False
        return True

    def get_latency(self):
        return random.randint(1, 1000) / 1000  # Convertir a segundos

    def run(self):
        initial_delay = random.uniform(0, interval)
        logger.info(f"{self.sensor_name}: Inicio retrasado {initial_delay:.1f}s")
        time.sleep(initial_delay)
        
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
                
            latency = self.get_latency()
            # Usar hora local para el display
            local_now = datetime.now().astimezone(TIMEZONE)
            logger.info(f"{self.sensor_name}: {local_now.strftime('%H:%M:%S')} (+{latency:.3f}s) | "
                     f"T:{self.prev_temperature:.1f}°->{self.temperature:.1f}° | "
                     f"H:{self.prev_humidity:.1f}%->{self.humidity:.1f}%")
            time.sleep(interval + latency)

if __name__ == "__main__":
    simulators = []
    
    # Start simulator threads
    for sensor in SENSORS:
        simulator = SensorSimulator(sensor)
        simulator.daemon = True
        simulator.start()
        simulators.append(simulator)

    # Show initial configuration
    logger.info(f"Intervalo de actualización configurado a {interval} segundos")
    logger.info(f"Simulando {len(SENSORS)} sensores")

    # Main loop
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)
