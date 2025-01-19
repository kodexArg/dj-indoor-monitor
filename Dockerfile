# Imagen base para el contenedor
FROM python:3.12-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE 1  # Evita escribir archivos .pyc
ENV PYTHONUNBUFFERED 1        # Habilita salida sin buffer en logs

# Instalar dependencias del sistema necesarias para el proyecto
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar e instalar dependencias de Python desde requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del proyecto al contenedor
COPY . /app/

# Crear directorio para archivos estáticos
RUN mkdir -p /app/staticfiles

# Configurar Django y recopilar archivos estáticos
RUN python manage.py collectstatic --noinput || echo "No se pudieron recopilar estáticos."

# Asignar permisos correctos a los archivos estáticos
RUN chmod -R 755 /app/staticfiles

# Exponer el puerto 8000 para la aplicación
EXPOSE 8000

# Comando predeterminado para iniciar la aplicación
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
