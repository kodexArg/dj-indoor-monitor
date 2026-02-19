# 6. Entorno de Producción y Despliegue

Esta sección detalla la arquitectura y consideraciones para desplegar el proyecto en un entorno de producción utilizando Docker, asegurando seguridad y escalabilidad.

## 6.1. Arquitectura de Despliegue

En producción, la aplicación se ejecuta dentro de contenedores Docker orquestados, separando responsabilidades.

```ascii
Internet (HTTPS)
   |
   v
+-----------+      +-----------+      +------------------+
|   Nginx   | ---> |  Webapp   | ---> |      Django      |
| (Reverse  |      | (Gunicorn)|      |   Application    |
|  Proxy)   |      +-----------+      +------------------+
+-----------+            |                     |
   |  ^                  v                     v
   |  |            +-----------+      +------------------+
   |  |            |   Redis   |      |   TimescaleDB    |
   |  |            |  (Cache)  |      |   (Database)     |
   |  |            +-----------+      +------------------+
   v  |
Static Files
(Volume)
```

## 6.2. Componentes de Infraestructura

### Nginx (Gateway)
Actúa como punto de entrada único.
*   **Archivos Estáticos**: Sirve directamente archivos CSS, JS e imágenes desde un volumen compartido (`staticfiles`), liberando a Django de esta carga.
*   **Proxy Reverso**: Reenvía las peticiones dinámicas al contenedor de la aplicación (`webapp`) en el puerto 8000.
*   **Configuración**: Definida en `nginx/nginx.conf`. Asegúrese de configurar `server_name` con su dominio real.

### Webapp (Django + Gunicorn)
Contenedor que ejecuta la lógica de la aplicación.
*   **Gunicorn**: Servidor WSGI de grado de producción.
*   **Entrypoint**: Gestiona las esperas de disponibilidad de base de datos antes de iniciar.

### Database (TimescaleDB)
Extensión de PostgreSQL optimizada para series temporales.
*   **Persistencia**: Los datos se almacenan en un volumen de Docker (`postgres`).
*   **Rendimiento**: Configurado en `docker-compose.yml` con parámetros de memoria ajustados.

### Redis (Caché - Opcional)
Disponible en la infraestructura (`docker-compose.yml`).
*   **Nota de Configuración**: Actualmente, `settings.py` está configurado por defecto para usar `LocMemCache`. Para habilitar Redis en producción, debe actualizar `CACHES` en `settings.py` para usar el backend de Redis y apuntar al servicio `redis`.

## 6.3. Variables de Entorno Críticas (.env)

En producción, es CRÍTICO configurar correctamente las variables de entorno para la seguridad:

*   `DJANGO_DEBUG=False`: **Obligatorio**.
*   `DJANGO_SECRET_KEY`: Debe ser una cadena larga, aleatoria y única.
*   `DJANGO_ALLOWED_HOSTS`: Lista de dominios permitidos (e.g., `misitio.com,www.misitio.com`).
*   `DB_*`: Credenciales de base de datos seguras.
*   `DOMAIN`: Dominio principal del sitio (para configuraciones de CORS/CSRF).

## 6.4. Pasos de Despliegue

1.  **Configurar Entorno**: Crear el archivo `.env` con valores de producción.
2.  **Construir Contenedores**:
    ```bash
    docker-compose -f docker-compose.yml build
    ```
    *Se recomienda usar `docker-compose.prod.yml` si existe uno específico, o sobreescribir configuraciones.*
3.  **Iniciar Servicios**:
    ```bash
    docker-compose -f docker-compose.yml up -d
    ```
4.  **Tareas Post-Despliegue**:
    *   Ejecutar migraciones: `docker-compose exec webapp python manage.py migrate`
    *   Recolectar estáticos: `docker-compose exec webapp python manage.py collectstatic --noinput`

## 6.5. Mantenimiento

*   **Logs**: `docker-compose logs -f --tail=100` para monitorear la actividad.
*   **Backups**: Realizar copias de seguridad periódicas del volumen de datos de PostgreSQL.
