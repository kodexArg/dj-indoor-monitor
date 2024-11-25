import sqlite3
from loguru import logger
import sys
import pandas as pd
import argparse

def delete_all_data(db_path):
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

def load_data(db_path):
    try:
        conn = sqlite3.connect(db_path)
        query = """
            SELECT 
                strftime('%Y-%m-%d %H:%M:%S', timestamp) as timestamp,
                sensor,
                t as temperature,
                h as humidity 
            FROM core_sensordata
            ORDER BY timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except sqlite3.Error as e:
        logger.error(f"Error al cargar datos: {e}")
        return None
    finally:
        if conn:
            conn.close()

def show_data(df):
    if df is None or df.empty:
        logger.warning("No hay datos para mostrar")
        return
    
    print("\n=== Primeros registros ===")
    print(df.head())
    print("\n=== Últimos registros ===")
    print(df.tail())

def show_info(df):
    if df is None or df.empty:
        logger.warning("No hay datos para analizar")
        return
    
    print("\n=== Información general ===")
    print(df.info())
    
    print("\n=== Estadísticas por sensor ===")
    for sensor in df['sensor'].unique():
        sensor_data = df[df['sensor'] == sensor]
        print(f"\nSensor: {sensor}")
        print(f"Registros: {len(sensor_data)}")
        print(f"Rango temporal: {sensor_data['timestamp'].min()} a {sensor_data['timestamp'].max()}")
        print("\nEstadísticas de temperatura y humedad:")
        print(sensor_data[['temperature', 'humidity']].describe())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Utilidad para gestionar datos de sensores en SQLite')
    parser.add_argument('action', nargs='?', default='show', choices=['delete', 'show', 'info'],
                        help='Acción a realizar: delete, show (default), o info')
    args = parser.parse_args()
    
    db_path = "../db.sqlite3"
    
    if args.action == 'delete':
        confirmation = input("¿Estás seguro de que quieres borrar todos los datos? (s/N): ")
        if confirmation.lower() == 's':
            delete_all_data(db_path)
        else:
            logger.info("Operación de borrado cancelada")
    else:
        df = load_data(db_path)
        if args.action == 'info':
            show_info(df)
        else:  # show
            show_data(df)