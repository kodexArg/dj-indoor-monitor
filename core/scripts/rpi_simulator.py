import requests
import time
from datetime import datetime

# Configuración
endpoint = "http://127.0.0.1:8000/api/sensordata/"
interval = 10  # Intervalo en segundos

def send_data():
    data = {
        "timestamp": datetime.now().isoformat(),
        "rpi": "sim_pi_01",
        "t": 25,
        "h": 40
    }
    response = requests.post(endpoint, json=data)
    if response.status_code == 201:
        print("Datos enviados correctamente")
    else:
        print(f"Error al enviar datos: {response.status_code}")

if __name__ == "__main__":
    while True:
        send_data()
        time.sleep(interval)
