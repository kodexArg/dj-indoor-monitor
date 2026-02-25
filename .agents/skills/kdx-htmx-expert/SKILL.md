---
name: kdx-htmx-expert
description: Django + HTMX expert for this project. Use when implementing HTMX interactions, creating partial templates, writing HTMX views, debugging HTMX behavior, or ensuring consistency with established project patterns (chart loading, polling, timeframe filters, sensor selection).
---

# Django + HTMX Expert (kdx-htmx-expert)

Expert guidance for HTMX development within this Django project. All patterns, conventions, and examples are derived from the actual codebase.

## Stack Context

- **Backend**: Django 5.1.3 + django-htmx middleware (`request.htmx`)
- **Templates**: Django template engine (not Jinja2)
- **CSS**: Skeleton CSS (lightweight, ~400 lines) — no utility classes like Tailwind
- **HTMX delivery**: Static file `core/static/js/htmx.min.js`, loaded in `base.html`
- **HTMX config**: No global swap override — each element specifies its swap strategy
- **CSRF**: Global via `<meta name="htmx-config">` in `base.html` — auto-injects `X-CSRFToken` header. No per-element CSRF needed.

## Project Conventions

### URL Patterns

HTMX chart generation endpoints use a flat naming scheme:

```python
# core/urls.py
path('generate_sensor/', GenerateSensorView.as_view(), name='generate_sensor'),
path('generate_gauge/', GenerateGaugeView.as_view(), name='generate-gauge'),
```

Standard page views (no HTMX prefix):
```python
path('charts/', ChartsView.as_view(), name='charts'),
path('charts/sensors/', SensorsView.as_view(), name='sensors'),
path('charts/gauges/', GaugesView.as_view(), name='gauges'),
path('charts/vpd/', VPDView.as_view(), name='vpd'),
path('charts/interactive/', InteractiveView.as_view(), name='interactive'),
```

**Rule**: New HTMX-only endpoints that generate partial content use a flat URL (not nested under `htmx/`). View class names end in `View`.

### Template Organization

```
core/templates/
├── layouts/base.html              # Base with HTMX, Luxon, CSRF meta
├── home.html
├── charts.html                    # Hub with HTMX loading + auto-update controls
├── charts/
│   ├── sensors.html               # HTMX chart grid with timeframe/room filters
│   ├── gauges.html                # Gauge grid (jQuery/AJAX update, not HTMX)
│   ├── vpd.html                   # Static Plotly + table (no HTMX)
│   └── interactive.html           # HTMX-driven multi-metric chart
└── partials/
    ├── hx-indicator.html          # HTMX loading bar
    └── navbar.html                # Context-aware navigation
```

**Rules**:
- Partials go in `partials/` (flat, no subdirectory split yet)
- Chart-specific templates in `charts/`
- No `_` prefix on partial names — use directory structure

### View Pattern for Chart Endpoints

Chart-generating HTMX views are class-based, return raw HTML:

```python
# core/views.py
@method_decorator(csrf_exempt, name='dispatch')
class GenerateSensorView(View):
    def post(self, request):
        sensor_name = request.POST.get('sensor')
        timeframe = request.POST.get('timeframe', '4h').lower()
        metric = request.POST.get('metric', 't')

        # Build data, generate Plotly chart
        chart_html, count = sensor_plot(df, sensor_name, metric, timeframe, start_date, end_date)

        if df.empty:
            return HttpResponse("<div class='no-data-alert'>No hay datos disponibles.</div>")

        return HttpResponse(chart_html)
```

**Rules**:
- Use `HttpResponse` — chart endpoints return HTML fragments, not full Django responses
- `csrf_exempt` on chart POSTs because HTMX includes the token via meta header
- Log timing with loguru: `logger.debug(f"Chart for {sensor}/{metric}: {count} pts in {elapsed:.2f}s")`
- Always handle empty data gracefully — return informative HTML, not an error

## Established Patterns

### Pattern 1: HTMX Chart Loading on Page Init

Sensor charts load asynchronously on page load. Each sensor container triggers its own request.

**Template** (`charts/sensors.html`):
```html
{% for room, metrics in data.items %}
  {% for metric, sensors in metrics.items %}
    {% for sensor in sensors %}
    <div class="sensor-container"
         hx-post="{% url 'generate_sensor' %}"
         hx-trigger="load"
         hx-swap="innerHTML"
         hx-vals='{"sensor": "{{ sensor.name }}", "timeframe": "{{ timeframe }}", "metric": "{{ metric }}"}'
         hx-indicator="#loading-bar">
      <div class="loading-placeholder">Cargando...</div>
    </div>
    {% endfor %}
  {% endfor %}
{% endfor %}
```

**Key attributes**:
- `hx-trigger="load"` — fires immediately on page load
- `hx-vals` — passes POST body as JSON (sensor, timeframe, metric)
- `hx-indicator="#loading-bar"` — shows the global loading bar
- `hx-swap="innerHTML"` — replaces container content with chart HTML

**View** (already shown above as `GenerateSensorView`).

### Pattern 2: Timeframe Filter via HTMX

Timeframe buttons reload ALL sensor charts on the page with a new timeframe.

**Template** (`charts/sensors.html`):
```html
<div class="timeframe-controls">
  {% for tf in timeframes %}
  <button hx-get="{% url 'sensors' %}?timeframe={{ tf }}"
          hx-target="#chart-grid"
          hx-swap="innerHTML"
          hx-push-url="true"
          class="button {% if timeframe == tf %}button-primary{% endif %}">
    {{ tf }}
  </button>
  {% endfor %}
</div>

<div id="chart-grid">
  <!-- Sensor chart containers generated here -->
</div>
```

**Rule**: For filter changes that affect the whole page layout, use `hx-push-url="true"` to update the browser URL so the state is bookmarkable.

### Pattern 3: Room Filter Dropdown

```html
<select name="room"
        hx-get="{% url 'sensors' %}"
        hx-trigger="change"
        hx-target="#chart-grid"
        hx-swap="innerHTML"
        hx-include="[name='timeframe']">
  <option value="all">Todas las salas</option>
  {% for room in rooms %}
  <option value="{{ room.id }}" {% if selected_room == room.id|stringformat:"s" %}selected{% endif %}>
    {{ room.name }}
  </option>
  {% endfor %}
</select>
```

**Rule**: Use `hx-include` to pass additional state (timeframe) alongside the triggered value.

### Pattern 4: Auto-Update Polling

The charts hub (`charts.html`) has a polling control for live data refresh.

```html
<!-- Polling trigger element (hidden) -->
<div id="auto-updater"
     hx-get="{% url 'charts' %}"
     hx-trigger="every 30s"
     hx-swap="none">
</div>

<!-- Start/stop controls -->
<button onclick="htmx.trigger('#auto-updater', 'htmx:abort')">Detener</button>
<button onclick="htmx.trigger('#auto-updater', 'htmx:resume')">Reanudar</button>
```

**Rule**: Use `hx-swap="none"` for side-effect-only requests. For true live chart updates, the existing `chart.js` and `gauges.js` handle the Plotly refresh — HTMX handles UI controls only.

### Pattern 5: Loading Indicator

Global loading bar for all HTMX requests:

```html
<!-- partials/hx-indicator.html -->
<div id="loading-bar" class="htmx-indicator">
  <div class="progress-bar"></div>
</div>
```

```css
/* Shown by HTMX automatically when any request with hx-indicator="#loading-bar" is active */
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator { display: block; }
```

**Rule**: Always add `hx-indicator="#loading-bar"` to chart-loading elements. Never add per-element spinners if the global bar works.

### Pattern 6: Silent Background Operations

For operations that update server state without DOM changes:

```html
<div hx-get="{% url 'some-ping-endpoint' %}"
     hx-trigger="load"
     hx-swap="none">
</div>
```

**Rule**: Use `hx-swap="none"` for side-effect requests (session updates, cache warming, logging).

## CSRF Protection

CSRF is handled **globally** via meta tag in `layouts/base.html`:

```html
<meta name="htmx-config" content='{"headers": {"X-CSRFToken": "{{ csrf_token }}"}}'>
```

This auto-injects `X-CSRFToken` on every HTMX request. Views that still need `csrf_exempt` (like `GenerateSensorView`) use `@method_decorator(csrf_exempt, name='dispatch')` because they accept POST from any origin.

**Rule**: Never add `[name='csrfmiddlewaretoken']` to `hx-include` — it's redundant. For new views that only accept authenticated requests, use `@login_required` instead of `csrf_exempt`.

## Detecting HTMX Requests in Views

Use django-htmx middleware (`request.htmx` attribute):

```python
def my_view(request):
    if request.htmx:
        return HttpResponse(render_to_string("partials/chart-partial.html", ctx, request=request))
    return render(request, "charts/full-page.html", ctx)
```

## Quick Reference: Response Headers

| Header | When to Use | Example |
|--------|-------------|---------|
| `HX-Refresh: true` | Full page state change needed | After config update |
| `HX-Trigger: eventName` | Cross-component communication | `sensorDataUpdated` |
| `HX-Redirect: /url/` | Navigate to another page | After form submit |

## Quick Reference: Attributes Used in This Project

| Attribute Combo | Pattern | Notes |
|-----------------|---------|-------|
| `hx-trigger="load"` + `hx-swap="innerHTML"` | Chart async load | Standard for sensor charts |
| `hx-trigger="change"` + `hx-include` | Room/timeframe filter | Passes multiple params |
| `hx-trigger="every 30s"` + `hx-swap="none"` | Auto-update polling | Side-effect only |
| `hx-push-url="true"` | Bookmarkable filters | Preserve URL state |
| `hx-indicator="#loading-bar"` | Show global loading bar | Always add to chart loaders |

## Testing HTMX Endpoints

Uses **pytest + pytest-django**. Tests go in `core/tests/test_views.py` or `core/tests/test_htmx_views.py`. Class names describe **user behavior**, not implementation.

```python
import pytest
from django.urls import reverse
from django.utils import timezone
from core.models import Room, Sensor, DataPoint


@pytest.mark.django_db
class TestUserViewsSensorChart:

    def setup_data(self, db):
        room = Room.objects.create(name="Test Room")
        sensor = Sensor.objects.create(name="sensor-01", room=room)
        now = timezone.now()
        for i in range(15):
            DataPoint.objects.create(
                sensor=sensor.name, metric='t',
                value=22.0 + i * 0.1,
                timestamp=now - timezone.timedelta(hours=i),
            )
        return sensor

    def test_chart_returns_html_fragment(self, client, db):
        # Given: sensor with data
        sensor = self.setup_data(db)

        # When: HTMX requests a sensor chart
        resp = client.post(
            reverse('generate_sensor'),
            {'sensor': sensor.name, 'timeframe': '4h', 'metric': 't'},
        )

        # Then: response is an HTML fragment (not full page)
        assert resp.status_code == 200
        assert b"<!DOCTYPE" not in resp.content
        assert b"plotly" in resp.content.lower() or b"<div" in resp.content

    def test_no_data_returns_empty_state(self, client, db):
        # Given: sensor with no data

        # When: HTMX requests chart for empty sensor
        resp = client.post(
            reverse('generate_sensor'),
            {'sensor': 'nonexistent-sensor', 'timeframe': '4h', 'metric': 't'},
        )

        # Then: returns informative HTML, not an error
        assert resp.status_code == 200
        assert b"<!DOCTYPE" not in resp.content
```

**Key rules**:
- `GenerateSensorView` is `csrf_exempt` — no CSRF token needed in tests
- Verify responses are HTML fragments (no `<!DOCTYPE`)
- Test empty data paths (sensors with no DataPoints)
- Use `django_assert_max_num_queries` to catch N+1 in chart endpoints

## Checklist: New HTMX Chart Endpoint

1. Add URL in `core/urls.py` using flat naming scheme
2. Create class-based view inheriting from `View`
3. Apply `@method_decorator(csrf_exempt, name='dispatch')` if accepting POSTs
4. Return `HttpResponse(chart_html)` for the happy path
5. Return descriptive `HttpResponse("<div>...")` for empty data
6. Log timing with `logger.debug(f"...{elapsed:.2f}s")`
7. Create partial template if needed (in `core/templates/partials/`)
8. Add `hx-indicator="#loading-bar"` in the template
9. Write tests in `core/tests/test_htmx_views.py` — empty state, fragment check, query count
