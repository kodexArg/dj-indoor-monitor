# Python
import asyncio
import json
import os
from abc import ABC, abstractmethod

# Third-party
import adafruit_dht
import board
from gpiozero import MCP3008
from loguru import logger
import requests
from typing import TypedDict, List, Union, Optional, Literal
import yaml
from yaml.error import YAMLError

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
    def __init__(self, name: str, hardware_type: str, param: int, metrics: List[str]):
        super().__init__(name, hardware_type, metrics)
        self.dht_object = (adafruit_dht.DHT22(board.D{param}) 
                          if hardware_type == "dht22" 
                          else adafruit_dht.DHT11(board.D{param}))
    
    def read(self) -> Optional[dict]:
        try:
            temperature = self.dht_object.temperature if 't' in self.metrics else None
            humidity = self.dht_object.humidity if 'h' in self.metrics else None
            return {k: v for k, v in {'t': temperature, 'h': humidity}.items() 
                   if k in self.metrics and v is not None}
        except Exception as e:
            logger.error(f"Error reading {self.name}: {str(e)}")
            return None

class SensorMCP3008(SensorInterface):
    def __init__(self, name: str, param: List[Union[int, str]], metrics: List[str]):
        super().__init__(name, "mcp3008", metrics)
        self.channel = param[0]
        self.metric_type = param[1]
        self.mcp = MCP3008(channel=self.channel)
    
    def read(self) -> Optional[dict]:
        try:
            value = self.mcp.value
            return {self.metric_type: value} if self.metric_type in self.metrics else None
        except Exception as e:
            logger.error(f"Error reading {self.name}: {str(e)}")
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
            if config["type"] in ["dht22", "dht11"]:
                return SensorDHT(
                    name=config["name"],
                    hardware_type=config["type"],
                    param=config["param"],
                    metrics=config["metrics"]
                )
            elif config["type"] == "mcp3008":
                return SensorMCP3008(
                    name=config["name"],
                    param=config["param"],
                    metrics=config["metrics"]
                )
            logger.error(f"Unsupported sensor type: {config['type']}")
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
class SensorConfig(TypedDict):
    name: str
    type: Literal['dht11', 'dht22', 'mcp3008']
    interval: int
    param: Union[int, List[Union[int, str]]]
    metrics: List[Literal['t', 'h', 's', 'l', 'r']]

class Config(TypedDict):
    raspberry_id: str
    api_urls: List[str]
    sensors: List[SensorConfig]

def load_config() -> Optional[Config]:
    config_path = os.path.join(os.path.dirname(__file__), 'rpi-sensor-config.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate each sensor configuration
        for sensor in config['sensors']:
            if not all(k in sensor for k in ['name', 'type', 'interval', 'param', 'metrics']):
                raise ValueError(f"Missing required fields in sensor config: {sensor}")
            
            if sensor['type'] not in ['dht11', 'dht22', 'mcp3008']:
                raise ValueError(f"Invalid sensor type: {sensor['type']}")
            
            if sensor['type'] == 'mcp3008':
                if not (isinstance(sensor['param'], list) and len(sensor['param']) == 2):
                    raise ValueError(f"Invalid MCP3008 parameters for sensor {sensor['name']}")
            
            if not all(m in ['t', 'h', 's', 'l', 'r'] for m in sensor['metrics']):
                raise ValueError(f"Invalid metrics for sensor {sensor['name']}")
        
        return config
    except (YAMLError, ValueError) as e:
        logger.error(f"Error in configuration: {str(e)}")
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
