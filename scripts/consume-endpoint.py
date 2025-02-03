import asyncio
import board
import adafruit_dht
import requests
from gpiozero import MCP3008
from datetime import datetime
from dotenv import load_dotenv
import os
from loguru import logger
import sys

# Configuración inicial y logging
logger.remove()
logger.add(sys.stderr, format="{time} - {message}", level="INFO")
load_dotenv()

# Parámetros globales
API_URL = os.getenv("API_URL")
RASPBERRY_PI = os.getenv("RASPBERRY_ID")

if not api_url or not raspberry_id:
    logger.critical("Faltan configuraciones en .env")
    sys.exit(1)

# =============================================
# Sección 1: Parámetros de configuración
# =============================================
configs = [
    {   # Ejemplo para sensores DHT
        'type': 'dht22',
        'interval': 10,
        'sensors': ['invernadero-1', 'invernadero-2'],
        'params': [4, 22]  
    },
    {   # Ejemplo para sensor MCP3008
        'type': 'mcp3008',
        'interval': 5,
        'sensors': ['sustrato-1', 'sustrato-2', 'luz-1'],
        'params': [(0, 's'), (1, 's'), (2, 'l')]
    }
]

# =============================================
# Sección 2: Funciones para tipos de sensores
# =============================================

# Common utility functions
async def send_metric(sensor_name, metric, value):
    payload = {
        # 'timestamp': datetime.now().isoformat(),
        # 'rpi': RASPBERRY_PI,
        'sensor': sensor_name,
        'metric': metric,
        'value': value
    }
    
    try:
        response = await asyncio.to_thread(requests.post, API_URL, json=payload)
        if response.status_code == 201:
            logger.info(f"{sensor_name} {metric}: {value} - ✅")
        else:
            logger.error(f"{sensor_name} {metric}: {value} - ❌ {response.status_code}")
    except Exception as e:
        logger.error(f"Error enviando {metric} de {sensor_name}: {str(e)}")

# DHT Sensors Handler
async def handle_dht_group(config):
    sensors = []
    for gpio in config['params']: 
        try:
            pin = getattr(board, f'D{gpio}')

            if config['type'] == 'dht22':
                sensor = adafruit_dht.DHT22(pin)
            elif config['type'] == 'dht11':
                sensor = adafruit_dht.DHT11(pin)
            else:
                logger.error(f"Tipo de sensor no soportado: {config['type']}")

            sensors.append(sensor)

        except Exception as e:
            logger.error(f"Error inicializando sensor en GPIO {gpio}: {str(e)}")
            return

    while True:
        for i, sensor in enumerate(sensors):
            name = config['sensors'][i]
            try:
                t = await asyncio.to_thread(sensor.temperature)
                h = await asyncio.to_thread(sensor.humidity)
                
                if None in (t, h) or not (-40 <= t <= 80) or not (0 <= h <= 100) or (0 <= t <= 1 and 0 <= h <= 1):
                    logger.warning(f"Datos inválidos en {name}")
                    continue
                
                await send_metric(name, 't', t)
                await send_metric(name, 'h', h)
                await asyncio.sleep(0.5)
                
            except RuntimeError as e:
                logger.warning(f"Error lectura {name}: {str(e)}")
            except Exception as e:
                logger.error(f"Error crítico en {name}: {str(e)}")
        
        await asyncio.sleep(config['interval'])

# MCP3008 Sensor Handler
async def handle_mcp3008_group(config):
    try:
        mcp = MCP3008()
    except Exception as e:
        logger.error(f"Error inicializando MCP3008: {str(e)}")
        return

    while True:
        for i, (channel, metric) in enumerate(config['params']):
            name = config['sensors'][i]
            try:
                value = await asyncio.to_thread(lambda: mcp.value)
                await send_metric(name, metric, float(value))
            except Exception as e:
                logger.error(f"Error lectura {name} (Canal {channel}): {str(e)}")
        
        await asyncio.sleep(config['interval'])


# =============================================
# Sección 3: Dispatcher (Strategy Pattern)
# =============================================
async def dispatcher():
    strategies = {
        'dht11': handle_dht_group,
        'dht22': handle_dht_group,
        'mcp3008': handle_mcp3008_group
    }
    
    tasks = []
    for config in configs:
        strategy = strategies.get(config['type'])
        tasks.append(asyncio.create_task(strategy(config)))
    
    await asyncio.gather(*tasks)


# Punto de entrada principal
if __name__ == "__main__":
    asyncio.run(dispatcher())