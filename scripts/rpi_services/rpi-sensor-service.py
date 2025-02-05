"""
Este script gestiona la lectura de sensores y la transmisión de datos en dispositivos Raspberry Pi.

Funcionalidad:
- Lee datos de sensores DHT (dht11, dht22), MCP3008 (para sustrato y luz) y sensores simulados ("fake").
- Configura los sensores mediante un archivo YAML, especificando tipo de sensor, intervalos de lectura, pines o canales, y métricas (temperatura, humedad, humedad del suelo, luz).
- Envía los datos obtenidos a uno o más endpoints API para centralizar la información de monitoreo.

Uso:
1. Personalizar el archivo de configuración 'rpi-sensor-config.yaml' para definir los sensores y sus parámetros.
2. En entornos ARM (Raspberry Pi), se inicializan las librerías específicas de hardware; en otros entornos se utilizan sensores simulados.
3. Ejecutar este script para iniciar el ciclo continuo de lectura de sensores y transmisión de datos a la API.

Este script está diseñado para desplegarse en múltiples Raspberry Pi, cada uno con diferentes configuraciones de sensores, permitiendo un monitoreo distribuido y centralizado a través de una API.
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
import datetime

# Third-party
from loguru import logger
import requests
from typing import TypedDict, List, Union, Optional, Literal, Dict
import yaml
from yaml.error import YAMLError
import random

# Importaciones condicionales para hardware
config_path = os.path.join(os.path.dirname(__file__), 'rpi-sensor-config.yaml')
with open(config_path, 'r') as f:
    IS_ARM = yaml.safe_load(f).get('arm', False)

if IS_ARM:
    try:
        import adafruit_dht
        import board
        from gpiozero import MCP3008
        HARDWARE_AVAILABLE = True
    except ImportError:
        HARDWARE_AVAILABLE = False
        logger.warning("Hardware libraries not available")
else:
    HARDWARE_AVAILABLE = False
    logger.info("Running in non-ARM mode, using fake sensors")

# =================================================
# INTERFACES
# =================================================
class SensorInterface(ABC):
    def __init__(self, name: str, hardware_type: str, metrics: List[str]):
        self._name = name
        self._hardware_type = hardware_type
        self._metrics = metrics

    @property
    def name(self) -> str:
        return self._name

    @property
    def hardware_type(self) -> str:
        return self._hardware_type

    @property
    def metrics(self) -> List[str]:
        return self._metrics

    @abstractmethod
    def read(self) -> Optional[dict]:
        pass

class TransmitterInterface(ABC):
    @abstractmethod
    async def send_data(self, sensor: str, metric: str, value: float):
        pass

# =================================================
# IMPLEMENTACION DE SENSORES (Sensores DHT y MCP3008)
# =================================================
class SensorDHT(SensorInterface):
    def __init__(self, name: str, hardware_type: str, params: List[dict], metrics: List[str]):
        if not IS_ARM:
            raise ValueError("Cannot initialize DHT sensor in non-ARM environment")
        if not HARDWARE_AVAILABLE:
            raise ValueError("Required hardware libraries not available")
        super().__init__(name, hardware_type, metrics)
        # Extraer el número de GPIO usando índice directo
        gpio_num = params[0]['gpio']
        pin = getattr(board, f'D{gpio_num}')
        if hardware_type == "dht22":
            self.dht_object = adafruit_dht.DHT22(pin)
        elif hardware_type == "dht11":
            self.dht_object = adafruit_dht.DHT11(pin)
        else:
            raise ValueError(f"Unsupported hardware type: {hardware_type}")
    
    def read(self) -> Optional[dict]:
        try:
            readings = {}
            if 't' in self.metrics:
                readings['t'] = self.dht_object.temperature
            if 'h' in self.metrics:
                readings['h'] = self.dht_object.humidity
            return readings if readings else None
        except Exception as e:
            logger.error(f"Error reading {self.name}: {str(e)}")
            return None

class SensorMCP3008(SensorInterface):
    def __init__(self, name: str, params: List[dict], metrics: List[str]):
        super().__init__(name, "mcp3008", metrics)
        # Acceder a channel y min_v mediante índices directos
        self.channel = params[0]['channel']
        self.min_v = params[1]['min_v']
        self.max_v = 3.3
        self.metric_type = metrics[0]
        self.mcp = MCP3008(channel=self.channel)
        # Agregar constante para sensor de luz
        self.lux_max = 1000 if self.metric_type == 'l' else None

    def voltage_to_lux(self, voltage):
        """Convierte voltaje a lux para sensores de luz"""
        if voltage <= self.min_v:
            return self.lux_max
        if voltage >= self.max_v:
            return 0
        lux = self.lux_max * (self.max_v - voltage) / (self.max_v - self.min_v)
        return lux

    def read(self) -> Optional[dict]:
        try:
            voltage = self.mcp.value * self.max_v
            if self.metric_type == 's':  # Sensor de sustrato
                value = ((self.max_v - voltage) / (self.max_v - self.min_v)) * 100
                value = max(0, min(100, value))
            elif self.metric_type == 'l':  # Sensor de luz
                value = self.voltage_to_lux(voltage)
            return {self.metric_type: round(value, 2)}
        except Exception as e:
            logger.error(f"Error reading {self.name}: {str(e)}")
            return None

class SensorFake(SensorInterface):
    def __init__(self, name: str, metrics: List[str]):
        super().__init__(name, "fake", metrics)
    
    def read(self) -> Optional[Dict[str, float]]:
        try:
            data = {}
            for metric in self.metrics:
                if metric == "t":  # Temperatura (15°C - 35°C)
                    base_value = 25.0
                    variation = random.uniform(-10, 10)
                    data["t"] = round(base_value + variation, 2)
                elif metric == "h":  # Humedad (30% - 90%)
                    base_value = 60.0
                    variation = random.uniform(-30, 30)
                    data["h"] = round(base_value + variation, 2)
                elif metric == "s":  # Humedad del suelo (0% - 100%)
                    base_value = 70.0
                    variation = random.uniform(-20, 20)
                    data["s"] = round(base_value + variation, 2)
                elif metric == "l":  # Luz (0% - 100%)
                    hour = datetime.datetime.now().hour
                    if 6 <= hour <= 18:  # Día
                        base_value = 80.0
                        variation = random.uniform(-20, 20)
                    else:  # Noche
                        base_value = 5.0
                        variation = random.uniform(-5, 5)
                    data["l"] = round(max(0, min(100, base_value + variation)), 2)
            return data
        except Exception as e:
            logger.error(f"Error simulating {self.name}: {str(e)}")
            return None

# =================================================
# IMPLEMENTACIÓN DE TRANSMISIÓN
# =================================================
class APITransmitter(TransmitterInterface):
    def __init__(self, api_urls, raspberry_id):
        self.api_urls = api_urls.split(',')  # Convertir string de URLs en lista
        self.raspberry_id = raspberry_id
    
    async def send_data(self, sensor, metric, value):
        payload = {
            "sensor": sensor,
            "metric": metric,
            "value": value
        }
        
        async def send_to_url(url):
            try:
                response = await asyncio.to_thread(
                    requests.post,
                    url.strip(),
                    json=payload,
                    timeout=5  # 5 seconds timeout
                )
                if response.status_code == 201:
                    logger.info(f"{url} - {sensor} {metric}: {value} - ✅")
                else:
                    logger.error(f"{url} - {sensor} {metric}: {value} - ❌ {response.status_code}")
            except requests.Timeout:
                logger.error(f"Timeout sending to {url} - {metric} from {sensor}")
            except Exception as e:
                logger.error(f"Error sending to {url} - {metric} from {sensor}: {str(e)}")
        
        # Enviar a todas las URLs en paralelo
        await asyncio.gather(*[send_to_url(url) for url in self.api_urls])

# =================================================
# FÁBRICA DE SENSORES 
# =================================================
class SensorFactory:
    @staticmethod
    def create_sensor(config: dict) -> Optional[SensorInterface]:
        try:
            if not IS_ARM:
                logger.warning(f"Creating Fake sensor instead of {config['hardware_type']} in non-ARM environment")
                return SensorFake(
                    name=config["name"],
                    metrics=config["metrics"]
                )
            if config["hardware_type"] in ["dht22", "dht11"]:
                return SensorDHT(
                    name=config["name"],
                    hardware_type=config["hardware_type"],
                    params=config["params"],
                    metrics=config["metrics"]
                )
            elif config["hardware_type"] == "mcp3008":
                return SensorMCP3008(
                    name=config["name"],
                    params=config["params"],
                    metrics=config["metrics"]
                )
            elif config["hardware_type"] == "fake":
                return SensorFake(
                    name=config["name"],
                    metrics=config["metrics"]
                )
            logger.error(f"Unsupported sensor type: {config['hardware_type']}")
            return None
        except Exception as e:
            logger.error(f"Error creating sensor {config['name']}: {str(e)}")
            return None

# =================================================
# MANAGER DE LECTURAS Y TRANSMISIÓN
# =================================================
class SensorManager:
    def __init__(self, sensors_config: List[dict], transmitter: TransmitterInterface):
        self.sensors = []
        self.transmitter = transmitter
        self.sensor_intervals = {}
        
        for config in sensors_config:
            # Acá se crea el sensor
            sensor = SensorFactory.create_sensor(config)
            if sensor:
                self.sensors.append(sensor)
                self.sensor_intervals[sensor.name] = config.get('interval', 5)
    
    async def run(self):
        tasks = [self.monitor_sensor(sensor) for sensor in self.sensors]
        await asyncio.gather(*tasks)
    
    async def monitor_sensor(self, sensor: SensorInterface):
        while True:
            values = sensor.read()
            if values:
                for metric, value in values.items():
                    await self.transmitter.send_data(sensor.name, metric, value)
            await asyncio.sleep(self.sensor_intervals[sensor.name])

# =================================================
# MAIN DISPATCHER
# =================================================
class DHTParams(TypedDict):
    gpio: int

class MCP3008Params(TypedDict):
    channel: int
    min_v: float

class SensorConfig(TypedDict):
    name: str
    hardware_type: Literal['dht11', 'dht22', 'mcp3008', 'fake']
    interval: int
    params: List[Union[DHTParams, MCP3008Params]]  # Lista de parámetros según el YAML
    metrics: List[Literal['t', 'h', 's', 'l']>

class Config(TypedDict):
    raspberry_id: str
    api_urls: List[str]
    sensors: List[SensorConfig]

def load_config() -> Optional[Config]:
    config_path = os.path.join(os.path.dirname(__file__), 'rpi-sensor-config.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        # Validar cada sensor
        for sensor in config['sensors']:
            required_fields = {'name', 'hardware_type', 'interval', 'params', 'metrics'}
            if not all(field in sensor for field in required_fields):
                missing = required_fields - sensor.keys()
                raise ValueError(f"Campos faltantes en {sensor['name']}: {missing}")
            if sensor['hardware_type'] not in ['dht11', 'dht22', 'mcp3008', 'fake']:
                raise ValueError(f"Tipo de sensor inválido en {sensor['name']}: {sensor['hardware_type']}")
            if sensor['hardware_type'] in ['dht11', 'dht22']:
                if not isinstance(sensor['params'], list) or len(sensor['params']) != 1:
                    raise ValueError(f"Parámetros inválidos para sensor DHT {sensor['name']}")
                dht_params = sensor['params'][0]
                if not isinstance(dht_params, dict) or 'gpio' not in dht_params:
                    raise ValueError(f"Parámetro 'gpio' faltante en sensor DHT {sensor['name']}")
                if not isinstance(dht_params['gpio'], int):
                    raise ValueError(f"El parámetro 'gpio' debe ser un número entero en sensor {sensor['name']}")
            elif sensor['hardware_type'] == 'mcp3008':
                if not isinstance(sensor['params'], list) or len(sensor['params']) != 2:
                    raise ValueError(f"Parámetros inválidos para MCP3008 {sensor['name']}")
                required_params = {'channel', 'min_v'}
                params_keys = {key for param in sensor['params'] for key in param.keys()}
                if not required_params.issubset(params_keys):
                    raise ValueError(f"Parámetros faltantes en {sensor['name']}: {required_params - params_keys}")
            valid_metrics = {'t', 'h', 's', 'l'}
            if not all(m in valid_metrics for m in sensor['metrics']):
                invalid = set(sensor['metrics']) - valid_metrics
                raise ValueError(f"Métricas inválidas en {sensor['name']}: {invalid}")
        return config
    except (YAMLError, ValueError) as e:
        logger.error(f"Error en configuración: {str(e)}")
        return None

def main():
    config = load_config()
    if not config:
        return
    
    transmitter = APITransmitter(','.join(config['api_urls']), config['raspberry_id'])
    sensor_manager = SensorManager(config['sensors'], transmitter)
    asyncio.run(sensor_manager.run())

if __name__ == "__main__":
    main()
