import time
import board
import adafruit_dht
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
from loguru import logger
import sys

# Configurar loguru
logger.remove()
logger.add(sys.stderr, format="{time} - {message}", level="INFO")

load_dotenv()
api_url = os.getenv("API_URL")
raspberry_id = os.getenv("RASPBERRY_ID")
sleep_interval = int(os.getenv("SLEEP_INTERVAL", 10))

if not api_url or not raspberry_id:
    logger.critical("Faltan configuraciones en .env")
    sys.exit(1)

# Inicializar los sensores
sensor_d4 = adafruit_dht.DHT11(board.D4)
sensor_d22 = adafruit_dht.DHT11(board.D22)

# Definir los identificadores
sensors = [
    {"sensor": sensor_d4, "name": "flora-d4"},
    {"sensor": sensor_d22, "name": "flora-d22"}
]

while True:
    for sensor_info in sensors:
        sensor = sensor_info["sensor"]
        sensor_name = sensor_info["name"]

        try:
            temperature = sensor.temperature
            humidity = sensor.humidity
            timestamp = datetime.now().isoformat()

            if temperature is None or humidity is None:
                logger.warning(f"Sensor {sensor_name} inactivo o datos nulos")
                continue

            if not (-40 <= temperature <= 80) or not (0 <= humidity <= 100):
                logger.error(f"Valores fuera de rango en {sensor_name}: Temp/Hum inválidos")
                continue

            data = {"timestamp": timestamp, "rpi": str(raspberry_id), "sensor": sensor_name, "t": temperature, "h": humidity}

            try:
                response = requests.post(api_url, json=data)
                if response.status_code == 201:
                    logger.info(f"{sensor_name}: {temperature}°C {humidity}% - ✅")
                else:
                    logger.error(f"{sensor_name}: {temperature}°C {humidity}% - ❌ {response.status_code}")
            except requests.ConnectionError:
                logger.error(f"{sensor_name}: Error de conexión: no se pudo contactar con el servidor")
            except requests.Timeout:
                logger.error(f"{sensor_name}: Error de tiempo de espera en la conexión")
            except requests.RequestException as e:
                logger.error(f"{sensor_name}: Error de solicitud: {e}")

        except RuntimeError:
            logger.warning(f"Fallo en lectura del sensor {sensor_name}; no se envía")
        except Exception as e:
            logger.critical(f"Error inesperado en {sensor_name}: {e}")

        # Pequeña demora entre lecturas de los sensores
        time.sleep(0.5)

    # Esperar el intervalo especificado antes de la siguiente iteración
    time.sleep(sleep_interval)
