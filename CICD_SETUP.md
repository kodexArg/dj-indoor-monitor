# Configuración de CI/CD para Servidor On-Premise

Esta guía explica cómo configurar el despliegue automático (CD) utilizando **GitHub Actions** con un **Self-Hosted Runner**. Esta es la opción más segura y robusta para servidores que están detrás de firewalls o en redes privadas, ya que no requiere abrir puertos de entrada (SSH) al internet público.

## 1. Preparar el Servidor

Asegúrate de que el servidor tenga instaladas las dependencias básicas:

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias para el Runner de GitHub (.NET Core dependencies)
sudo apt install -y curl libdigest-sha-perl
```

## 2. Crear y Configurar el Runner en GitHub

1. Ve a tu repositorio en GitHub: `https://github.com/kodexArg/dj-indoor-monitor` (ajusta la URL a tu repo real).
2. Navega a **Settings** > **Actions** > **Runners**.
3. Haz clic en **New self-hosted runner**.
4. Selecciona **Linux**.
5. Sigue las instrucciones que aparecen en pantalla para descargar y configurar el agente en tu servidor. Serán algo así:

   ```bash
   # Crear carpeta
   mkdir actions-runner && cd actions-runner

   # Descargar paquete (la versión puede variar, usa el link de GitHub)
   curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

   # Extraer
   tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

   # Configurar (te pedirá token y nombre, usa los por defecto)
   ./config.sh --url https://github.com/kodexArg/dj-indoor-monitor --token <TOKEN_GENERADO_POR_GITHUB>
   ```

   **Nota:** Cuando te pregunte por etiquetas, puedes dejar las por defecto (`self-hosted`, `Linux`, `X64`).

6. Una vez configurado, instálalo como servicio para que se ejecute en background y reinicie automáticamente:

   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

## 3. Configurar la Rama (Branch)

El workflow está configurado para dispararse **solo cuando hay cambios en la rama `on-premise`**.

1. Crea la rama `on-premise` si no existe:
   ```bash
   git checkout -b on-premise
   git push -u origin on-premise
   ```

2. A partir de ahora, cada vez que hagas un merge o push a esta rama, el servidor descargará los cambios y ejecutará `docker compose up -d --build` automáticamente.

## 4. Troubleshooting

- **Permisos de Docker**: Si el runner falla con errores de permiso de Docker, asegúrate de que el usuario que ejecuta el runner (usualmente tu usuario actual si no especificaste otro en `./config.sh`) pertenece al grupo `docker`:
  ```bash
  sudo usermod -aG docker $USER
  # (Requiere reiniciar sesión o el servicio del runner)
  sudo ./svc.sh stop
  sudo ./svc.sh start
  ```
- **Logs**: Puedes ver el progreso y logs de cada despliegue en la pestaña **Actions** de tu repositorio en GitHub.
