# Entorno de Producción

Esta sección detalla la arquitectura y consideraciones para desplegar el proyecto en un entorno de producción utilizando Docker.

## Arquitectura de Despliegue

En producción, la aplicación se ejecuta dentro de contenedores Docker orquestados, separando responsabilidades para seguridad y rendimiento.

```ascii
Internet
   |
   v
+-----------+      +-----------+      +------------------+
|   Nginx   | ---> |  Gunicorn | ---> |      Django      |
| (Reverse  |      |  (WSGI)   |      |   Application    |
|  Proxy)   |      +-----------+      +------------------+
+-----------+            |                     |
   |  ^                  v                     v
   |  |            +-----------+      +------------------+
   |  |            |   Redis   |      |   TimescaleDB    |
   |  |            |  (Cache)  |      |   (Database)     |
   v  |            +-----------+      +------------------+
Static Files
(Volume)
```

## Componentes

### Nginx (Gateway)
Actúa como punto de entrada único.
*   **Archivos Estáticos**: Sirve directamente archivos CSS, JS e imágenes desde un volumen compartido (`staticfiles`), liberando a Django de esta carga.
*   **Proxy Reverso**: Reenvía las peticiones dinámicas al contenedor de la aplicación (`webapp`) en el puerto 8000.
*   **Seguridad**: Puede configurarse para manejar SSL/TLS (HTTPS).

### Webapp (Django + Gunicorn)
Contenedor que ejecuta la lógica de la aplicación.
*   **Gunicorn**: Servidor WSGI de grado de producción, configurado para manejar múltiples workers.
*   **Entrypoint**: El script `entrypoint.sh` se encarga de esperar a que la base de datos esté lista antes de iniciar el servidor.

### Database (TimescaleDB)
Extensión de PostgreSQL optimizada para series temporales.
*   **Persistencia**: Los datos se almacenan en un volumen de Docker (`postgres`) para sobrevivir al reinicio de contenedores.
*   **Rendimiento**: Configurado en `docker-compose.yml` con parámetros de memoria ajustados (`shared_buffers`, `effective_cache_size`) para cargas de trabajo típicas.

## Consideraciones de Configuración (`.env`)

En producción, es CRÍTICO configurar correctamente las variables de entorno:

*   `DEBUG=False`: **Obligatorio**. Evita filtrar información sensible en las páginas de error.
*   `SECRET_KEY`: Debe ser una cadena larga, aleatoria y única.
*   `ALLOWED_HOSTS`: Lista de dominios o IPs permitidas para acceder al sitio (e.g., `misitio.com, 192.168.1.50`).
*   `DB_*`: Credenciales de base de datos seguras y robustas.

## Pasos de Despliegue

1.  **Preparar Servidor**: Asegurarse de que Docker y Docker Compose estén instalados.
2.  **Configurar Entorno**: Crear el archivo `.env` con valores de producción.
3.  **Construir Contenedores**:
    ```bash
    docker-compose -f docker-compose.yml build
    ```
4.  **Iniciar Servicios**:
    ```bash
    docker-compose -f docker-compose.yml up -d
    ```
5.  **Tareas Post-Despliegue**:
    *   Ejecutar migraciones: `docker-compose exec webapp python manage.py migrate`
    *   Recolectar estáticos: `docker-compose exec webapp python manage.py collectstatic --noinput` (Esto copia los archivos al volumen compartido con Nginx).

## Mantenimiento

*   **Logs**: `docker-compose logs -f --tail=100` para monitorear la actividad.
*   **Backups**: Realizar copias de seguridad periódicas del volumen de datos de PostgreSQL.
*   **Actualizaciones**: `git pull`, reconstruir imágenes y reiniciar contenedores.
