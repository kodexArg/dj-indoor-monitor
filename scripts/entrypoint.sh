#!/bin/bash
set -e

until PGPASSWORD=$DB_PASSWORD psql -h "db" -U "$DB_USER" -d "$DB_NAME" -c '\q'; do
  echo "PostgreSQL no disponible - esperando..."
  sleep 1
done

echo "PostgreSQL listo!"

python manage.py migrate --no-input
python manage.py collectstatic --no-input

exec gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -