# 1. Copiar el archivo CSV del contenedor remoto al servidor remoto
ssh kodex@kcbd-monitor.grupoalvs.com -p 2222 "docker cp postgres_db:/tmp/core_sensordata.csv /home/kodex/core_sensordata.csv"

# 2. Copiar el archivo CSV desde el servidor remoto a tu máquina local
scp -P 2222 kodex@kcbd-monitor.grupoalvs.com:/home/kodex/core_sensordata.csv ./core_sensordata.csv

# 3. Copiar el archivo CSV desde tu máquina local al contenedor local
docker cp ./core_sensordata.csv postgres_db:/tmp/core_sensordata.csv

# 4. Vaciar la tabla core_sensordata en tu base de datos local
docker exec -it postgres_db psql -U kodex_user -d dj_db -c "TRUNCATE TABLE core_sensordata;"

# 5. Importar los datos del archivo CSV a la tabla core_sensordata
docker exec -it postgres_db psql -U kodex_user -d dj_db -c "\copy core_sensordata FROM '/tmp/core_sensordata.csv' CSV HEADER;"

# 6. Verificar que los datos se han importado correctamente
docker exec -it postgres_db psql -U kodex_user -d dj_db -c "SELECT * FROM core_sensordata LIMIT 10;"

