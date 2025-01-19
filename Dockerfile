FROM python:3.12-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente al contenedor
COPY . /app/

# Crear directorio para archivos estáticos y manejar errores en collectstatic
RUN mkdir -p /app/staticfiles \
    && python manage.py collectstatic --noinput || echo "Collectstatic failed, skipping."

# Asignar permisos correctos al directorio estático
RUN chmod -R 755 /app/staticfiles

# Exponer puerto de la aplicación
EXPOSE 8000

# Comando de inicio
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
