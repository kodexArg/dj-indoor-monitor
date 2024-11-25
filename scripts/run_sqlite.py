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
        query = "SELECT * FROM core_sensordata"
        df = pd.read_sql_query(query, conn)
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
    
    print("\n=== Estadísticas descriptivas ===")
    print(df.describe())
    
    if 'timestamp' in df.columns:
        print("\n=== Rango temporal de datos ===")
        print(f"Primer registro: {df['timestamp'].min()}")
        print(f"Último registro: {df['timestamp'].max()}")
        print(f"Total registros: {len(df)}")

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