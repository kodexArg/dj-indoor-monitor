# Frontend

El frontend del proyecto se caracteriza por su ligereza y eficiencia, delegando la mayor parte de la lógica de renderizado al servidor (Django) y utilizando librerías minimalistas para la interactividad y el estilo.

## Tecnologías y Librerías

*   **HTML5 Semántico**: Base de la estructura de las páginas.
*   **Skeleton CSS**: Un boilerplate CSS extremadamente ligero que proporciona una rejilla (grid) responsiva y estilos básicos limpios. Se complementa con `Normalize.css` para consistencia entre navegadores.
*   **HTMX**: Motor de interactividad. Se utiliza para realizar peticiones asíncronas al servidor y actualizar partes del DOM (gráficos, tablas) sin recargar la página completa. Esto proporciona una experiencia de usuario fluida (tipo SPA) sin la complejidad de JavaScript del lado del cliente.
*   **Plotly.js**: Librería de gráficos utilizada para renderizar las visualizaciones de datos. Aunque los datos y la configuración del gráfico se preparan en el backend, Plotly.js se encarga del dibujo interactivo en el navegador.
*   **Luxon**: Librería para el manejo y formateo de fechas y horas en JavaScript.

## Estructura de Plantillas (Templates)

El proyecto utiliza el sistema de plantillas de Django con herencia:

*   **`layouts/base.html`**: Plantilla maestra. Define la estructura HTML común (`<head>`, `header`, `footer`), carga los archivos estáticos (CSS/JS) y define bloques (`{% block content %}`) que las páginas específicas sobrescriben.
*   **`partials/`**: Fragmentos de HTML reutilizables.
    *   `navbar.html`: Barra de navegación.
    *   `hx-indicator.html`: Indicador de carga visual para peticiones HTMX.
*   **`charts/`**: Plantillas específicas para visualizaciones.
    *   `sensors.html`: Panel principal de sensores.
    *   `interactive.html`: Interfaz para gráficos históricos interactivos.
    *   `vpd.html`: Visualización del Déficit de Presión de Vapor.
    *   `gauges.html`: Panel de medidores tipo "gauge".

## Organización de Archivos Estáticos

Los recursos estáticos se encuentran en `core/static/` y se organizan en:

*   `css/`: Hojas de estilo (`styles.css` para personalizaciones propias, `skeleton.css`, `normalize.css`).
*   `js/`: Scripts de terceros (`htmx.min.js`, `plotly.min.js`) y scripts propios (`gauges.js`, `charts.js`) que manejan inicializaciones específicas.
*   `images/` e `icons/`: Recursos gráficos y logotipos.

## Flujo de Interacción Típico

1.  El usuario carga una página (e.g., `/charts/interactive/`).
2.  Django renderiza la plantilla base y el contenido inicial.
3.  El usuario interactúa con un control (e.g., cambia el rango de fechas).
4.  HTMX intercepta el evento y envía una petición GET/POST al backend con los nuevos parámetros.
5.  El backend procesa la solicitud y devuelve un fragmento de HTML (e.g., el `<div>` del gráfico actualizado).
6.  HTMX reemplaza el contenido antiguo en el DOM con el nuevo fragmento.
