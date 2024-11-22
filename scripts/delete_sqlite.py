import sqlite3
from loguru import logger
import sys

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

if __name__ == "__main__":
    db_path = "../db.sqlite3"  
    delete_all_data(db_path)