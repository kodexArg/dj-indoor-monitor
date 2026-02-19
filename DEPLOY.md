# Guía de Despliegue en Servidor On-Premise (192.168.6.11)

Esta guía detalla los pasos para poner en producción la nueva instancia del monitor de clima en el servidor 192.168.6.11.

## Requisitos Previos

- **Docker** y **Docker Compose** instalados en el servidor.
- Acceso a este repositorio (GitHub).

## Pasos de Instalación

1.  **Clonar el Repositorio**
    ```bash
    git clone <URL_DEL_REPO> dj-indoor-monitor
    cd dj-indoor-monitor
    ```

2.  **Configurar Variables de Entorno**
    Crea el archivo `.env` basándote en el ejemplo proporcionado:
    ```bash
    cp .env.example .env
    nano .env
    ```
    
    Asegúrate de configurar las siguientes variables críticas para el entorno 192.168.6.11:
    ```ini
    # Configuración de Dominio/IP
    DOMAIN=192.168.6.11
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.6.11
    
    # Base de Datos (Credenciales seguras)
    DB_PASSWORD=<tupasswordsecreto>
    
    # Seguridad (Para entorno sin SSL/HTTPS directo)
    BEHIND_SSL_PROXY=False
    CSRF_COOKIE_SECURE=False
    SESSION_COOKIE_SECURE=False
    ```

3.  **Levantar los Servicios**
    Ejecuta el siguiente comando para construir e iniciar los contenedores:
    ```bash
    docker-compose up -d --build
    ```

4.  **Verificación**
    - Accede a `http://192.168.6.11/` para ver el dashboard.
    - Accede a `http://192.168.6.11:8000/` para verificar que el puerto 8000 responde (espejo del puerto 80).

## Compatibilidad con Sensores

Los sensores están configurados para enviar datos a:
- `http://192.168.6.11:8000/api/data-point/`

La configuración actual de `docker-compose.yml` mapea el puerto 8000 del host al puerto 80 del contenedor Nginx, asegurando que esta URL funcione correctamente sin necesidad de reconfigurar los sensores.

## Mantenimiento

- **Ver logs**: `docker-compose logs -f webapp`
- **Reiniciar servicios**: `docker-compose restart`
- **Actualizar**:
    ```bash
    git pull
    docker-compose up -d --build
    ```
