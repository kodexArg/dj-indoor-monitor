import argparse
import asyncio
import datetime
import random
import sqlite3
from loguru import logger
from typing import List

def delete_all_data(db_path: str) -> None:
    """
    Elimina todos los datos de la tabla 'core_sensordata' en la base de datos especificada.

    Args:
        db_path (str): Ruta a la base de datos SQLite.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM core_sensordata") 
        conn.commit()
        logger.info("Datos eliminados de 'core_sensordata'.")
    except sqlite3.Error as e:
        logger.error(f"Error al eliminar datos: {e}")
    finally:
        if conn:
            conn.close()

async def insert_data(sensor: str, timestamp: str, temperature: float, humidity: float) -> None:
    """
    Inserta datos simulados en la tabla 'core_sensordata' de la base de datos.

    Args:
        sensor (str): Nombre del sensor.
        timestamp (str): Marca de tiempo en formato ISO 8601.
        temperature (float): Valor simulado de temperatura.
        humidity (float): Valor simulado de humedad.
    """
    logger.debug(f"Insertando: {timestamp}, {sensor}, T={temperature}, H={humidity}")
    try:
        conn = sqlite3.connect('../db.sqlite3')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO core_sensordata (timestamp, sensor, t, h) VALUES (?, ?, ?, ?)
        """, (timestamp, sensor, temperature, humidity))
        conn.commit()
        logger.info(f"{timestamp}, {sensor}, T={temperature}, H={humidity}")  # Short log line
    except sqlite3.Error as e:
        logger.error(f"Error al insertar datos: {e}")
    finally:
        if conn:
            conn.close()

async def get_sensors(sensor_count: int) -> List[str]:
    """
    Genera una lista de nombres de sensores simulados.

    Args:
        sensor_count (int): Número de sensores a generar.

    Returns:
        List[str]: Lista de nombres de sensores simulados.
    """
    sensors = [f"simu-sensor-{i:02d}" for i in range(1, sensor_count + 1)]
    logger.info(f"Sensores generados: {sensors}")
    return sensors

async def generate_data(sensor: str, timestamps: List[datetime.datetime], seconds: int) -> None:
    """
    Genera datos simulados para un sensor específico en paralelo.

    Args:
        sensor (str): Nombre del sensor.
        timestamps (List[datetime.datetime]): Lista de marcas de tiempo.
        seconds (int): Intervalo de tiempo en segundos entre cada dato simulado.
    """
    logger.info(f"Generando datos para: {sensor}")
    try:
        tasks = []
        for timestamp in timestamps:
            temperature: float = round(random.uniform(15.0, 30.0), 1)  # Temperatura simulada
            humidity: float = round(random.uniform(30.0, 70.0), 1)     # Humedad simulada
            tasks.append(insert_data(sensor, timestamp.isoformat(), temperature, humidity))
            logger.debug(f"Preparado: {timestamp.isoformat()}, {sensor}, T={temperature}, H={humidity}")
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error al generar datos para {sensor}: {e}")

async def main() -> None:
    """
    Función principal que orquesta la limpieza de la base de datos y la generación de datos simulados.
    """
    logger.info("Iniciando limpieza de la base de datos")
    delete_all_data('../db.sqlite3') 

    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', help='Fecha de inicio en formato ISO 8601 (por defecto 2 días atrás)')
    parser.add_argument('--seconds', type=int, default=60, help='Intervalo de tiempo en segundos')
    parser.add_argument('--sensors', type=int, default=3, help='Cantidad de sensores')
    args = parser.parse_args()

    if args.start_date:
        start_date: datetime.datetime = datetime.datetime.fromisoformat(args.start_date)
    else:
        start_date = datetime.datetime.now() - datetime.timedelta(days=2)
    logger.info(f"Fecha de inicio: {start_date}")

    current_time: datetime.datetime = datetime.datetime.now()
    logger.info(f"Fecha actual: {current_time}")

    sensor_count: int = args.sensors
    sensors: List[str] = await get_sensors(sensor_count)
    logger.info(f"Número de sensores: {sensor_count}")

    timestamps = []
    while current_time >= start_date:
        timestamps.append(current_time)
        current_time -= datetime.timedelta(seconds=args.seconds)

    tasks: List[asyncio.Task] = []
    for sensor in sensors:
        tasks.append(generate_data(sensor, timestamps, args.seconds))
        logger.debug(f"Tarea creada para: {sensor}")

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.warning("Proceso interrumpido por el usuario")

if __name__ == '__main__':
    """
    Punto de entrada del script. Inicia la ejecución de la función principal.
    """
    logger.info("Iniciando script async_history_generator.py")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Script detenido por el usuario")
