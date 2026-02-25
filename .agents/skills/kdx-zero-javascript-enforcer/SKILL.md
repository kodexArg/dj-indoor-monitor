---
name: kdx-zero-javascript-enforcer
description: Enforces HTMX-first policy for UI interactivity in this project. Acknowledges visualization libraries (Plotly, Gauge.js, Luxon) as foundational. Activates when about to write NEW JavaScript for UI interactions. Forces HTMX-first evaluation before any custom JS. Visualization integration JS is allowed; UI interaction JS is not.
---

# HTMX-First Enforcer (kdx-zero-javascript-enforcer)

**This skill is a GATE.** Before writing ANY new JavaScript for UI interactions — including inline `<script>`, new event handlers, or new `.js` files — you MUST run through the Decision Tree below and document which tier applies.

## The Context: This Is a Visualization-Heavy Project

This project uses JavaScript visualization libraries as **foundational infrastructure**. These are NOT subject to this policy:

| Library | Role | Policy |
|---------|------|--------|
| **Plotly** (`plotly-2.35.2.min.js`) | Chart rendering (server-generated HTML injected via HTMX) | ✅ Foundational |
| **Gauge.js** (`gauge.min.js`) | Real-time gauge rendering | ✅ Foundational |
| **Luxon** (`luxon.min.js`) | Timezone-aware datetime formatting | ✅ Foundational |
| **chart.js** (custom) | Auto-update interval, latest data fetch | ✅ Foundational |
| **gauges.js** (custom) | Plotly gauge refresh via `Plotly.restyle` | ✅ Foundational |
| **timing.js** (custom) | HTMX request instrumentation | ✅ Foundational |
| **HTMX** (`htmx.min.js`) | UI interactions, chart loading | ✅ Foundational |

**If your need relates to visualization data display or chart rendering → extend the existing JS files above.**

**If your need relates to UI interaction, navigation, filtering, or form behavior → read the Decision Tree below.**

## The Iron Rule

> **UI interaction JavaScript is technical debt.** Every custom JS event handler is logic that can't be tested with pytest, can't use Django's ORM, and can't benefit from template inheritance. When HTMX can do it, HTMX must do it.

## Decision Tree (Mandatory, Top-Down)

Evaluate EVERY new UI interactivity requirement in this exact order. Stop at the first tier that solves the problem.

```
┌──────────────────────────────────────────────────────────┐
│  REQUIREMENT: UI interaction / dynamic behavior          │
│  (NOT visualization data rendering — see exempt list)    │
└──────────────────────┬───────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   TIER 1: HTMX  │  ← DEFAULT. Always try this first.
              │   + Server-Side  │
              │   Python/Django  │
              └────────┬────────┘
                       │ Can't solve it?
              ┌────────▼────────┐
              │  TIER 2: HTML5  │  ← Native browser capabilities
              │  Native Elements │
              └────────┬────────┘
                       │ Can't solve it?
              ┌────────▼──────────────────────────────────────┐
              │ TIER 3: Vanilla JS (inline, ≤30 lines)        │
              │ ONLY for: visualization integration,          │
              │ browser APIs (clipboard, file reader),        │
              │ or extending existing foundational JS files   │
              └───────────────────────────────────────────────┘
```

---

## Tier 1: HTMX + Server-Side Python (DEFAULT)

**When to use**: ALWAYS try this first. Covers ~90% of interactivity needs.

This is the project's primary interaction model for UI. Logic lives in Python, tested with pytest.

### What HTMX Handles

| Need | HTMX Solution | Custom JS Needed? |
|------|---------------|------------|
| Load chart on scroll/init | `hx-trigger="load"` | No |
| Timeframe filter | `hx-get` + page re-render | No |
| Room filter dropdown | `hx-trigger="change"` + `hx-include` | No |
| Reload charts after filter | `hx-get` + `hx-target` | No |
| Bookmarkable filter state | `hx-push-url="true"` | No |
| Loading indicator | `hx-indicator="#loading-bar"` + CSS | No |
| Pagination | `hx-get` with page param | No |
| Toggle visibility | Server returns different HTML | No |
| Delete with confirmation | `hx-confirm` + `hx-delete` | No |
| Update multiple elements | `hx-swap-oob="true"` | No |
| Live sensor update | `hx-trigger="every 30s"` | No |

### Project Patterns (Already Established)

See `kdx-htmx-expert` for full pattern catalog. Key patterns:

**Chart loading** (replaces manual fetch in templates):
```html
<div class="sensor-container"
     hx-post="{% url 'generate_sensor' %}"
     hx-trigger="load"
     hx-swap="innerHTML"
     hx-vals='{"sensor": "{{ sensor.name }}", "timeframe": "{{ timeframe }}", "metric": "{{ metric }}"}'
     hx-indicator="#loading-bar">
</div>
```

**Timeframe filter** (replaces JS click handlers):
```html
<button hx-get="{% url 'sensors' %}?timeframe={{ tf }}"
        hx-target="#chart-grid"
        hx-swap="innerHTML"
        hx-push-url="true">
  {{ tf }}
</button>
```

**Room filter** (replaces JS `onchange` handlers):
```html
<select hx-get="{% url 'sensors' %}"
        hx-trigger="change"
        hx-target="#chart-grid"
        hx-include="[name='timeframe']">
```

### The Python-First Sub-Rule

When the solution involves **computing, transforming, or deciding** what to show — that logic MUST live in Python:

```python
# CORRECT: Logic in Python (GenerateSensorView), rendered server-side
def post(self, request):
    df = DataPointDataFrameBuilder(...).build(...)
    chart_html, count = sensor_plot(df, sensor_name, metric, timeframe, ...)
    return HttpResponse(chart_html)
```

```javascript
// WRONG: Same logic duplicated in JavaScript
function fetchAndRenderChart(sensor, metric) {
    // Duplicates DataPointDataFrameBuilder logic — don't do this
    fetch(`/api/data-point/?sensor=${sensor}&metric=${metric}`)
        .then(data => renderPlotly(data));
}
```

---

## Tier 2: HTML5 Native Elements

**When to use**: Pure presentation interactions that don't need server communication.

| Need | HTML5 Solution |
|------|----------------|
| Expandable section | `<details><summary>` |
| Modal/dialog | `<dialog>` with `showModal()` |
| Tooltips | `title` attribute or CSS `:hover` |
| Form validation | `required`, `pattern`, `min`, `max` |
| Date picker | `<input type="date">` |
| Range slider | `<input type="range">` |
| Progress indicator | `<progress>` or `<meter>` |

### Example: Expandable Sensor Details (No JS)

```html
<!-- CORRECT: Native HTML5 -->
<details>
    <summary>Detalles del sensor {{ sensor.name }}</summary>
    <dl>
        <dt>Room</dt><dd>{{ sensor.room.name }}</dd>
        <dt>Last value</dt><dd>{{ last_value }} °C</dd>
    </dl>
</details>
```

```javascript
// WRONG: JavaScript accordion
document.querySelector('.sensor-header').addEventListener('click', function() {
    this.nextElementSibling.classList.toggle('hidden');
});
```

---

## Tier 3: Vanilla JavaScript (NARROW EXCEPTIONS ONLY)

**When to use**: Only when ALL of these are true:
1. HTMX cannot solve it (no server roundtrip makes sense)
2. HTML5 native elements cannot solve it
3. The need is specifically: visualization integration, browser API access, or extending existing foundational files

### Valid Tier 3 Use Cases

| Need | Why Not Higher Tiers? | Where |
|------|----------------------|-------|
| Plotly chart resize on window resize | Plotly-specific API | Extend `chart.js` or `gauges.js` |
| Gauge color update on value threshold | Plotly.restyle is JS-only | Extend `gauges.js` |
| Clipboard copy of sensor value | Browser Clipboard API | Inline in template |
| File download trigger | Browser API | Inline in template |
| Timing integration with HTMX events | `htmx:beforeRequest` hook | Extend `timing.js` |
| Canvas rendering (future) | Canvas API | New file, justified |

### Vanilla JS Rules (Non-Negotiable)

1. **Prefer extending existing files** — If the logic belongs in visualization, add it to `chart.js`, `gauges.js`, or `timing.js`. These are the project's JS modules.
2. **Inline in template** if it's page-specific and < 30 lines — `<script>` block at bottom of template.
3. **No new `.js` files** for UI interactions — the JS bundle should NOT grow for UI features.
4. **Scoped to the page** — No global state, no `window.*` exports beyond what already exists.
5. **Maximum 30 lines** — If your inline script exceeds 30 lines, re-evaluate whether HTMX covers part of it.
6. **Document WHY** — Add a comment: `<!-- JS required: Plotly API not callable via HTMX -->`

### Template-Inline Pattern

```html
{% block scripts %}
<!-- JS required: Plotly responsive resize requires imperative JS call -->
<script>
(function() {
    window.addEventListener('resize', function() {
        const charts = document.querySelectorAll('.plotly-graph-div');
        charts.forEach(el => Plotly.relayout(el, {autosize: true}));
    });
})();
</script>
{% endblock %}
```

---

## Current Foundational JS Files

These files are established and should be extended, not duplicated:

| File | Role | When to Extend |
|------|------|----------------|
| `core/static/js/chart.js` | Auto-update interval, fetch `/api/sensor-data/latest/` | Need new sensor metric display |
| `core/static/js/gauges.js` | Plotly.restyle gauge updates, visibility detection | Need gauge styling or new gauge type |
| `core/static/js/timing.js` | HTMX request timing instrumentation | Need new timing metrics |

**Key insight**: The Plotly chart HTML itself is generated **server-side** by `core/charts.py` via `sensor_plot()`, `gauge_plot()`, `interactive_chart()`. HTMX injects the resulting HTML into the DOM. The JS files only handle **updates to already-rendered charts**.

---

## Enforcement Checklist

Before implementing ANY new interactivity, answer these questions:

- [ ] **Is this visualization rendering?** → Use existing Plotly/Gauge.js pipeline (Python generates, HTMX injects)
- [ ] **Can HTMX handle this?** Even if it means an extra endpoint, HTMX is preferred for UI.
- [ ] **Can HTML5 native elements handle this?** `<details>`, `<dialog>`, form validation attributes.
- [ ] **If Vanilla JS is truly needed**: Is it < 30 lines? Does it belong in an existing foundational file?
- [ ] **Did I add a comment explaining WHY?** `<!-- JS required: [reason HTMX doesn't apply] -->`

## Mandatory Justification Format

When proposing ANY new custom JavaScript (Tier 3), include this in your response:

```
### JS Justification
- **Tier applied**: 3 (Vanilla JS)
- **Why not HTMX**: [specific reason]
- **Why not HTML5 native**: [specific reason]
- **Visualization-related**: [yes/no — if yes, which library and why]
- **Lines of JS**: [number]
- **Location**: [inline in which template | extend which existing .js file]
```

---

## Quick Reference: Common "I Need JS" Scenarios

| "I need JS for..." | Actually use... | Tier |
|--------------------|--------------------|------|
| Load chart on page load | `hx-trigger="load"` on chart container | 1 |
| Filter charts by timeframe | `hx-get` button with `hx-push-url` | 1 |
| Filter charts by room | `hx-trigger="change"` on select | 1 |
| Auto-refresh chart data | `hx-trigger="every 30s"` or extend `chart.js` | 1/3 |
| Show/hide element | HTMX swap or `<details>` | 1/2 |
| Expandable section | `<details><summary>` | 2 |
| Modal | `<dialog>` + HTMX | 2+1 |
| Plotly chart update (new value) | Extend `gauges.js` with `Plotly.restyle` | 3 |
| New chart type | Add to `core/charts.py` (Python) + generate via HTMX | 1 |
| Clipboard copy | Inline `navigator.clipboard` | 3 |
| Drag-and-drop | Vanilla JS (valid but rare) | 3 |
