FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio static y ejecutar collectstatic
RUN mkdir -p /app/static && \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
