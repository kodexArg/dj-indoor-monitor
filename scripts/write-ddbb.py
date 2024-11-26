import sys
import os
import asyncio
from datetime import datetime, timedelta
import argparse

# Añadir el directorio actual al sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sensortoddbb import loop_write_values, delete_all_data

# Constants
SENSORS = ['flora-01', 'flora-02', 'vege-03', 'secado-04']

def prepare_arguments():
    parser = argparse.ArgumentParser(description="Insert sensor data into the database for multiple sensors.")
    parser.add_argument('--seconds', type=int, default=5, help='Seconds between timestamps (default: 5)')
    parser.add_argument('--start-date', type=str, default=(datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S'), help='Start date (default: 48 hours ago)')
    parser.add_argument('--end-date', type=str, default=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'), help='End date (default: 1 hour in the future)')
    parser.add_argument('--delete', action='store_true', help='Delete all data before inserting new data')
    
    return parser.parse_args()

async def main():
    args = prepare_arguments()
    
    if args.delete:
        delete_all_data('../db.sqlite3')
    
    tasks = []
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d %H:%M:%S')
    
    for sensor in SENSORS:
        tasks.append(loop_write_values(sensor, start_date, args.seconds, stop_time=end_date))
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
