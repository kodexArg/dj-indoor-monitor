from loguru import logger
import asyncio
import random
import sys
import argparse
import os
from datetime import datetime

def analizar_argumentos():
    parser = argparse.ArgumentParser(description='Generar datos falsos de sensores')
    parser.add_argument('--segundos', type=float, required=True, help='Intervalo entre lecturas en segundos')
    parser.add_argument('--sensores', type=int, required=True, help='Número de sensores a simular')
    parser.add_argument('--borrar-bbdd', action='store_true', help='Eliminar la base de datos SQLite si existe')
    return parser.parse_args()

def eliminar_base_datos():
    ruta_db = os.path.join('db.sqlite3')
    if os.path.exists(ruta_db):
        os.remove(ruta_db)
        logger.success("Base de datos eliminada exitosamente")
    else:
        logger.warning("Archivo de base de datos no encontrado")

async def generar_datos_sensor(id_sensor: int) -> dict:
    return {
        "sensor_id": id_sensor,
        "temperatura": round(random.uniform(20, 30), 2),
        "humedad": round(random.uniform(30, 70), 2),
        "timestamp": datetime.now().isoformat()
    }

async def monitorear_sensores(num_sensores: int, intervalo: float):
    while True:
        # Genera datos para todos los sensores concurrentemente
        tareas = [generar_datos_sensor(i) for i in range(num_sensores)]
        lecturas = await asyncio.gather(*tareas)
        
        # Registra los resultados
        for lectura in lecturas:
            logger.info(f"Sensor {lectura['sensor_id']}: "
                     f"Temp: {lectura['temperatura']}°C, "
                     f"Humedad: {lectura['humedad']}%")
        logger.debug("-" * 50)
        
        try:
            await asyncio.sleep(intervalo)
        except asyncio.CancelledError:
            break

async def main():
    args = analizar_argumentos()
    
    if args.borrar_bbdd:
        eliminar_base_datos()
        return

    try:
        await monitorear_sensores(args.sensores, args.segundos)
    except KeyboardInterrupt:
        logger.info("\nApagando el sistema de manera ordenada...")
    except asyncio.CancelledError:
        logger.info("\nApagando el sistema de manera ordenada...")

if __name__ == "__main__":
    # Configuración básica de loguru
    logger.remove()
    logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Programa terminado por el usuario")