import sys
import os
import asyncio
from datetime import datetime, timedelta
import argparse
import psycopg2
from psycopg2 import sql

# Añadir el directorio actual al sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sensortoddbb import loop_write_values

# Constants
SENSORS = ['flora-01', 'flora-02', 'vege-03', 'secado-04']

def prepare_arguments():
    parser = argparse.ArgumentParser(description="Insert sensor data into the database for multiple sensors.")
    parser.add_argument('--seconds', type=int, default=5, help='Seconds between timestamps (default: 5)')
    parser.add_argument('--start-date', type=str, default=(datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S'), help='Start date (default: 48 hours ago)')
    parser.add_argument('--end-date', type=str, default=(datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'), help='End date (default: 30 minutes in the future)')
    parser.add_argument('--delete', action='store_true', help='Delete all data before inserting new data')
    
    return parser.parse_args()

def delete_all_data(db_name: str, db_user: str, db_password: str, db_host: str, db_port: str) -> bool:
    confirmation = input("¿Está seguro de que desea eliminar todos los datos? (s/n): ")
    if confirmation.lower() != 's':
        print("Eliminación de datos cancelada.")
        return False

    conn = None
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        cursor = conn.cursor()
        cursor.execute(sql.SQL("DELETE FROM core_sensordata"))
        conn.commit()
        print("Datos eliminados de 'core_sensordata'.")
        return True
    except psycopg2.Error as e:
        print(f"Error al eliminar datos: {e}")
        return False
    finally:
        if conn:
            cursor.close()
            conn.close()

async def main():
    args = prepare_arguments()
    
    if args.delete:
        if not delete_all_data(
            db_name=os.getenv('DB_NAME'),
            db_user=os.getenv('DB_USER'),
            db_password=os.getenv('DB_PASSWORD'),
            db_host=os.getenv('DB_HOST'),
            db_port=os.getenv('DB_PORT')
        ):
            sys.exit("Error al eliminar datos. Cerrando el script.")
        sys.exit("Datos eliminados correctamente. Cerrando el script.")
    
    tasks = []
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d %H:%M:%S')
    
    for sensor in SENSORS:
        tasks.append(loop_write_values(sensor, start_date, args.seconds, stop_time=end_date))
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
