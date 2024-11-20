import requests
import time
import random
from datetime import datetime
import threading

# Configuración
endpoint = "http://127.0.0.1:8000/api/sensor-data/"
interval = 10  # Intervalo en segundos
RPIS = ["simu_pi_01", "simu_pi_02", "simu_pi_03"]

class RpiSimulator(threading.Thread):
    def __init__(self, rpi_name):
        threading.Thread.__init__(self)
        self.rpi_name = rpi_name
        self.running = True
        self.temperature = 22.0
        self.humidity = 60.0
        self.prev_temperature = self.temperature
        self.prev_humidity = self.humidity

    def update_temperature(self):
        self.prev_temperature = self.temperature
        if random.random() < 0.1:  # 10% de probabilidad
            variation = random.choice([-0.5, -0.4, -0.3, -0.2, -0.1, 0.1, 0.2, 0.3, 0.4, 0.5])
            self.temperature += variation
            self.temperature = round(min(35.0, max(15.0, self.temperature)), 1)

    def update_humidity(self):
        self.prev_humidity = self.humidity
        if random.random() < 0.05:  # 5% de probabilidad
            variation = random.randint(-2, 2)
            self.humidity += variation
            self.humidity = round(min(80.0, max(20.0, self.humidity)), 1)

    def send_data(self):
        data = {
            "timestamp": datetime.now().isoformat(),
            "rpi": self.rpi_name,
            "t": self.temperature,
            "h": self.humidity
        }
        response = requests.post(endpoint, json=data)

    def get_latency(self):
        return random.randint(1, 1000) / 1000  # Convertir a segundos

    def run(self):
        initial_delay = random.uniform(0, interval)
        print(f"{self.rpi_name}: Inicio retrasado {initial_delay:.1f}s")
        time.sleep(initial_delay)
        
        while self.running:
            self.update_temperature()
            self.update_humidity()
            self.send_data()
            latency = self.get_latency()
            print(f"{self.rpi_name}: {datetime.now().strftime('%H:%M:%S')} (+{latency:.3f}s) | "
                  f"T: {self.prev_temperature:.1f}° -> {self.temperature:.1f}° | "
                  f"H: {self.prev_humidity:.1f}% -> {self.humidity:.1f}%")
            time.sleep(interval + latency)

if __name__ == "__main__":
    simulators = []
    for rpi in RPIS:
        simulator = RpiSimulator(rpi)
        simulator.start()
        simulators.append(simulator)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo simuladores...")
        for simulator in simulators:
            simulator.running = False
            simulator.join()
        print("Simuladores detenidos")
