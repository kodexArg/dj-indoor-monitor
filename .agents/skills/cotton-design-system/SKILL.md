---
name: cotton-design-system
description: Build reusable UI components with django-cotton and Skeleton CSS. Use when creating component libraries, implementing reusable UI patterns, standardizing HTML components across templates, or setting up the django-cotton component system for this project.
---

# Django Cotton + Skeleton CSS Design System

Build scalable, reusable UI components for this Django project using **django-cotton** for component composition and **Skeleton CSS** for responsive styling.

> **Current stack:** Skeleton CSS (lightweight, ~400 lines). django-cotton is planned but not yet installed. This skill prepares patterns for when it's added.

## Setup

### Install django-cotton

```bash
pip install django-cotton
```

Add to `project/settings.py`:

```python
INSTALLED_APPS = [
    ...
    'django_cotton',
]
```

No additional configuration needed — django-cotton auto-discovers components from the `cotton/` directory inside your templates folder.

---

## Core Concepts

### 1. Component Location

Components live in `cotton/` inside your templates directory:

```
core/templates/
├── cotton/                         # Component library
│   ├── button.html                 # <c-button>
│   ├── card.html                   # <c-card>
│   ├── alert.html                  # <c-alert>
│   ├── badge.html                  # <c-badge>
│   ├── metric-card.html            # <c-metric-card> (sensor value display)
│   ├── chart-container.html        # <c-chart-container> (HTMX chart loader)
│   ├── gauge-container.html        # <c-gauge-container>
│   └── timeframe-selector.html     # <c-timeframe-selector>
├── layouts/base.html
├── charts/
└── partials/
```

### 2. Component Syntax

```html
<!-- Usage in any template: -->
<c-button>Click me</c-button>

<!-- With attributes (props): -->
<c-button variant="primary" size="large">Save</c-button>

<!-- With named slots: -->
<c-card>
    <c-slot name="header">Sensor Data</c-slot>
    <p>Content here</p>
</c-card>
```

### 3. Props (vars attribute)

```html
<!-- core/templates/cotton/button.html -->
<c-vars variant="default" size="normal" type="button" />

<button type="{{ type }}"
        class="button {% if variant == 'primary' %}button-primary{% endif %} {% if size == 'large' %}u-full-width{% endif %}">
    {{ slot }}
</button>
```

### 4. Slots

```html
<!-- core/templates/cotton/card.html -->
<div class="card">
    {% if header %}
    <div class="card-header">{{ header }}</div>
    {% endif %}
    <div class="card-body">
        {{ slot }}
    </div>
    {% if footer %}
    <div class="card-footer">{{ footer }}</div>
    {% endif %}
</div>
```

Usage:
```html
<c-card>
    <c-slot name="header">Room A — Temperature</c-slot>
    <p>Current: 23.5°C</p>
    <c-slot name="footer">Last updated: 2 min ago</c-slot>
</c-card>
```

### 5. Pass-through Attributes (attrs)

```html
<!-- core/templates/cotton/input.html -->
<c-vars label="" help_text="" error="" />

<div class="form-group">
    {% if label %}<label>{{ label }}</label>{% endif %}
    <input class="u-full-width {% if error %}error{% endif %}" {{ attrs }}>
    {% if help_text %}<span class="help-text">{{ help_text }}</span>{% endif %}
    {% if error %}<span class="error-text">{{ error }}</span>{% endif %}
</div>
```

Usage:
```html
<c-input label="Temperature" name="temp" type="number" min="0" max="50"
         help_text="In Celsius" placeholder="22.0">
```

---

## Skeleton CSS Foundations

Skeleton CSS uses a **12-column fluid grid** with minimal utility classes.

### Grid System

```html
<div class="container">
    <div class="row">
        <div class="four columns">Column 1 (4/12)</div>
        <div class="four columns">Column 2 (4/12)</div>
        <div class="four columns">Column 3 (4/12)</div>
    </div>
</div>
```

Column classes: `one` through `twelve` + `one-third`, `two-thirds`, `one-half`.

### Typography

```html
<h1>Heading 1</h1>   <!-- 5.0rem -->
<h2>Heading 2</h2>   <!-- 4.2rem -->
<h3>Heading 3</h3>   <!-- 3.6rem -->
<h4>Heading 4</h4>   <!-- 3.0rem -->
<h5>Heading 5</h5>   <!-- 2.4rem -->
<h6>Heading 6</h6>   <!-- 1.5rem -->
```

### Buttons

```html
<!-- Default button -->
<a class="button" href="#">Default</a>
<button class="button">Default</button>

<!-- Primary (filled) -->
<button class="button button-primary">Primary</button>

<!-- Full width -->
<button class="button u-full-width">Full Width</button>
```

### Forms

```html
<div class="row">
    <div class="six columns">
        <label for="exampleEmailInput">Email</label>
        <input class="u-full-width" type="email" placeholder="test@mailbox.com" id="exampleEmailInput">
    </div>
    <div class="six columns">
        <label for="exampleSelect">Example Select</label>
        <select class="u-full-width" id="exampleSelect">
            <option value="Option 1">Option 1</option>
        </select>
    </div>
</div>
```

### Tables

```html
<table class="u-full-width">
    <thead>
        <tr><th>Sensor</th><th>Room</th><th>Temp</th><th>Humidity</th></tr>
    </thead>
    <tbody>
        <tr><td>sensor-01</td><td>Room A</td><td>23.5°C</td><td>65%</td></tr>
    </tbody>
</table>
```

---

## Project-Specific Component Patterns

### Pattern 1: Sensor Metric Card

Displays current sensor value with metric-specific styling.

**Component** (`cotton/metric-card.html`):
```html
<c-vars sensor="" metric="" value="" unit="" room="" last_update="" />

<div class="metric-card" data-sensor="{{ sensor }}" data-metric="{{ metric }}">
    <div class="metric-header">
        <span class="metric-label">{{ metric }}</span>
        <span class="metric-room">{{ room }}</span>
    </div>
    <div class="metric-value">
        <span class="value">{{ value }}</span>
        <span class="unit">{{ unit }}</span>
    </div>
    {% if last_update %}
    <div class="metric-footer">{{ last_update }}</div>
    {% endif %}
</div>
```

**Usage**:
```html
{% for sensor_data in gauges_by_room %}
<c-metric-card
    sensor="{{ sensor_data.sensor }}"
    metric="t"
    value="{{ sensor_data.temp }}"
    unit="°C"
    room="{{ sensor_data.room }}">
</c-metric-card>
{% endfor %}
```

### Pattern 2: HTMX Chart Container

Lazy-loads a Plotly chart via HTMX POST on page init.

**Component** (`cotton/chart-container.html`):
```html
<c-vars sensor="" metric="t" timeframe="4h" title="" loading_text="Cargando..." />

<div class="chart-wrapper">
    {% if title %}
    <h5 class="chart-title">{{ title }}</h5>
    {% endif %}
    <div class="sensor-container"
         hx-post="{% url 'generate_sensor' %}"
         hx-trigger="load"
         hx-swap="innerHTML"
         hx-vals='{"sensor": "{{ sensor }}", "timeframe": "{{ timeframe }}", "metric": "{{ metric }}"}'
         hx-indicator="#loading-bar">
        <p class="loading-text">{{ loading_text }}</p>
    </div>
</div>
```

**Usage**:
```html
{% for sensor in active_sensors %}
<div class="four columns">
    <c-chart-container
        sensor="{{ sensor.name }}"
        metric="t"
        timeframe="{{ timeframe }}"
        title="{{ sensor.name }} — Temperature">
    </c-chart-container>
</div>
{% endfor %}
```

### Pattern 3: Timeframe Selector

HTMX-powered timeframe filter buttons.

**Component** (`cotton/timeframe-selector.html`):
```html
<c-vars current="" target="#chart-grid" redirect_url="" />

<div class="timeframe-selector">
    {% for tf, label in timeframes %}
    <button class="button {% if current == tf %}button-primary{% endif %}"
            hx-get="{{ redirect_url }}?timeframe={{ tf }}"
            hx-target="{{ target }}"
            hx-swap="innerHTML"
            hx-push-url="true">
        {{ label }}
    </button>
    {% endfor %}
</div>
```

**Usage**:
```html
<c-timeframe-selector
    current="{{ timeframe }}"
    redirect_url="{% url 'sensors' %}"
    target="#chart-grid">
</c-timeframe-selector>
```

### Pattern 4: Alert / Notification

**Component** (`cotton/alert.html`):
```html
<c-vars type="info" dismissible="false" />

<div class="alert alert-{{ type }}" role="alert">
    {{ slot }}
    {% if dismissible == "true" %}
    <button type="button" class="alert-close" onclick="this.parentElement.remove()">×</button>
    {% endif %}
</div>
```

**Usage**:
```html
<c-alert type="warning">
    Sensor "sensor-03" has not reported data in 2 hours.
</c-alert>

<c-alert type="info" dismissible="true">
    Showing data for the last 4 hours.
</c-alert>
```

### Pattern 5: Data Table

Reusable sensor data table with room grouping.

**Component** (`cotton/sensor-table.html`):
```html
<c-vars caption="" empty_message="No hay datos disponibles." />

<table class="u-full-width">
    {% if caption %}
    <caption>{{ caption }}</caption>
    {% endif %}
    <thead>{{ header }}</thead>
    <tbody>
        {% if rows %}
        {{ rows }}
        {% else %}
        <tr><td colspan="99" class="empty-message">{{ empty_message }}</td></tr>
        {% endif %}
    </tbody>
    {% if footer %}<tfoot>{{ footer }}</tfoot>{% endif %}
</table>
```

**Usage**:
```html
<c-sensor-table caption="VPD por sala" empty_message="Sin datos en las últimas 24h">
    <c-slot name="header">
        <tr><th>Sala</th><th>Sensor</th><th>Temp</th><th>Humedad</th><th>VPD</th></tr>
    </c-slot>
    <c-slot name="rows">
        {% for row in room_data %}
        <tr>
            <td>{{ row.room }}</td>
            <td>{{ row.sensor }}</td>
            <td>{{ row.t|floatformat:1 }}°C</td>
            <td>{{ row.h|floatformat:0 }}%</td>
            <td>{{ row.vpd|floatformat:2 }} kPa</td>
        </tr>
        {% endfor %}
    </c-slot>
</c-sensor-table>
```

---

## Component Library Checklist

When creating a new component:

1. Place in `core/templates/cotton/<component-name>.html`
2. Define props with `<c-vars prop1="default1" prop2="default2" />`
3. Use `{{ slot }}` for default content, `{{ named_slot }}` for named slots
4. Use `{{ attrs }}` to pass through HTML attributes to the root element
5. Keep components focused — one concern per component
6. Use Skeleton CSS classes for styling (no custom CSS if Skeleton covers it)
7. Document usage with a comment block at the top of the component file

### Component Documentation Block

```html
{{#
  Component: chart-container
  Description: Lazy-loads a Plotly sensor chart via HTMX POST

  Props:
    sensor (required): Sensor name string matching DataPoint.sensor field
    metric: Metric code ('t', 'h', 'l', 's') — default: 't'
    timeframe: Time window ('1min', '30min', '1h', '4h', '1d') — default: '4h'
    title: Optional heading above the chart
    loading_text: Placeholder text while chart loads — default: 'Cargando...'

  Usage:
    <c-chart-container sensor="sensor-01" metric="t" timeframe="4h" title="Temperature">
    </c-chart-container>
#}}
```

---

## Best Practices

### Do's

- **One component per file** — each cotton component does one thing
- **Sensible defaults** — all props should have default values via `<c-vars>`
- **Skeleton first** — use Skeleton CSS classes before adding custom CSS
- **HTMX in components** — components CAN contain HTMX attributes (e.g., `chart-container`)
- **Slot-based composition** — prefer slots over complex prop APIs

### Don'ts

- **Don't nest components more than 3 levels deep** — gets hard to debug
- **Don't put business logic in components** — components render data, views compute it
- **Don't duplicate Skeleton classes** — use existing `.button`, `.u-full-width`, etc.
- **Don't add JavaScript in components** — JS goes in templates or foundational JS files

---

## Migration Plan: Current Templates → Cotton Components

| Current Pattern | Candidate Component |
|----------------|---------------------|
| Sensor chart `<div>` with HTMX attrs | `<c-chart-container>` |
| Timeframe buttons in sensors.html | `<c-timeframe-selector>` |
| VPD data table (vpd.html) | `<c-sensor-table>` |
| Loading placeholder text | `<c-loading-placeholder>` |
| Gauge container div | `<c-gauge-container>` |
| Navbar links | Keep in `partials/navbar.html` (not a component) |

Start with the most-repeated patterns (chart container, metric card) to maximize reuse impact.
