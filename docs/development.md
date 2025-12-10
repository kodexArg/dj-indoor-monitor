# Entorno de Desarrollo

Esta guía describe cómo configurar y ejecutar el proyecto en un entorno local para propósitos de desarrollo y pruebas.

## Prerrequisitos

*   **Docker** y **Docker Compose**: Para ejecutar la infraestructura completa (BD, Redis, App) en contenedores.
*   **Python 3.12+**: Si se desea ejecutar el backend fuera de Docker.
*   **Git**: Para el control de versiones.

## Configuración Inicial

1.  **Clonar el repositorio**:
    ```bash
    git clone <url-del-repositorio>
    cd dj-indoor-monitor
    ```

2.  **Configurar Variables de Entorno**:
    Crear un archivo `.env` en la raíz del proyecto basándose en un ejemplo (si existe) o definiendo las siguientes claves críticas:
    ```ini
    DEBUG=True
    SECRET_KEY=tu_clave_secreta_desarrollo
    DB_NAME=postgres
    DB_USER=postgres
    DB_PASSWORD=postgres
    DB_HOST=db
    DB_PORT=5432
    ALLOWED_HOSTS=localhost,127.0.0.1
    ```

## Ejecución con Docker (Recomendado)

El proyecto incluye un archivo `docker-compose.yml` que orquesta todos los servicios necesarios.

1.  **Construir y levantar servicios**:
    ```bash
    docker-compose up --build
    ```
    Esto iniciará:
    *   `db`: Base de datos TimescaleDB (PostgreSQL optimizado).
    *   `redis`: Servidor de caché.
    *   `webapp`: Aplicación Django.
    *   `nginx`: Servidor web (aunque en desarrollo se puede acceder directamente al puerto de Django si se expone).

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

## Ejecución Local (Sin Docker)

Para desarrollo rápido de backend sin levantar todos los contenedores (requiere una BD Postgres local o accesible):

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

3.  **Configurar BD**:
    Asegurarse de tener PostgreSQL corriendo y ajustar el `.env` para apuntar a `localhost` en lugar de `db`.

4.  **Ejecutar servidor**:
    ```bash
    python manage.py runserver
    ```

## Flujo de Trabajo

*   Los cambios en el código Python (`.py`) reiniciarán automáticamente el servidor de desarrollo (tanto en Docker como local).
*   Los cambios en plantillas HTML se reflejan al recargar la página.
*   Los cambios en archivos estáticos pueden requerir ejecutar `python manage.py collectstatic` si se está sirviendo a través de Nginx, o simplemente recargar si `DEBUG=True` y Django los sirve.
