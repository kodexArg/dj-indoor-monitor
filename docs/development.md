# 5. Entorno de Desarrollo y Configuración Local

Esta guía describe cómo configurar y ejecutar el proyecto en un entorno local para propósitos de desarrollo y pruebas.

## 5.1. Prerrequisitos

*   **Docker** y **Docker Compose**: Para ejecutar la infraestructura completa (BD, Redis, App) en contenedores.
*   **Python 3.12+**: Si se desea ejecutar el backend fuera de Docker.
*   **Git**: Para el control de versiones.

## 5.2. Configuración Inicial (.env)

El proyecto requiere variables de entorno para funcionar. Crea un archivo `.env` en la raíz del proyecto. Estas variables configuran la conexión a la base de datos, claves secretas y comportamiento del logging.

```ini
# --- Django Core ---
DJANGO_SECRET_KEY="tu_clave_secreta_local_dev"
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
# Nivel de Log de aplicación (usando Loguru)
DJANGO_LOGURU_LEVEL=DEBUG
# Nivel de Log de Django (usando logging nativo)
DJANGO_LOG_LEVEL=DEBUG
# Idioma por defecto
DJANGO_DEFAULT_LANGUAGE_CODE=es-ar

# --- Base de Datos (PostgreSQL/TimescaleDB) ---
# Si usas Docker (nombre del servicio):
# DB_HOST=db
# Si corres localmente contra un Postgres en tu máquina o remoto:
DB_ENGINE=django.db.backends.postgresql
DB_NAME=dj_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
# DB_LOCAL se usa si ejecutas 'python manage.py runserver' fuera del contenedor
DB_LOCAL=localhost

# --- Configuración Regional ---
DJANGO_TIMEZONE=America/Argentina/Buenos_Aires

# --- Seguridad (Local) ---
# En local, estos valores suelen ser False
BEHIND_SSL_PROXY=False
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False

# --- Dominio ---
DOMAIN=localhost

# --- Sensores ---
# Lista separada por comas de sensores a ignorar en ciertas vistas
IGNORE_SENSORS=sensor_prueba_1,sensor_roto
```

## 5.3. Ejecución con Docker (Recomendado)

El proyecto incluye un archivo `docker-compose.yml` que orquesta todos los servicios necesarios.

1.  **Construir y levantar servicios**:
    ```bash
    docker-compose up --build
    ```
    Esto iniciará:
    *   `db`: Base de datos TimescaleDB.
    *   `redis`: Servidor de caché (Nota: Aunque Redis se levanta, la configuración actual de Django (`settings.py`) puede estar usando `LocMemCache` por defecto. Verifica `CACHES` en `settings.py`).
    *   `webapp`: Aplicación Django.
    *   `nginx`: Servidor web (puerto 80).

2.  **Aplicar migraciones**:
    ```bash
    docker-compose exec webapp python manage.py migrate
    ```

3.  **Crear superusuario**:
    ```bash
    docker-compose exec webapp python manage.py createsuperuser
    ```

4.  **Acceder al sitio**:
    Navegar a `http://localhost`.

## 5.4. Ejecución Local (Sin Docker)

Para desarrollo rápido de backend sin levantar todos los contenedores (requiere una BD Postgres accesible):

1.  **Crear entorno virtual**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    .\venv\Scripts\activate   # Windows
    ```

2.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar servidor**:
    ```bash
    python manage.py runserver
    ```

## 5.5. Flujo de Trabajo

*   Los cambios en el código Python (`.py`) reiniciarán automáticamente el servidor de desarrollo.
*   Los cambios en plantillas HTML se reflejan al recargar la página.
