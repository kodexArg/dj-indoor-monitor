---
name: kdx-qa-for-django
description: Generate test plans, pytest test cases, regression suites, and bug reports for this Django project. Uses pytest + pytest-django (v4.9.0) with Django's testing tools. Focused on models, views, HTMX endpoints, DRF API endpoints, utilities, and chart generation functions.
trigger: explicit
---

# QA for Django (kdx-qa-for-django)

Behavior-Driven Testing skill for this Django project. Tests describe **user behavior**, not implementation details. Uses **pytest + pytest-django** as the test runner, with **Django's built-in testing tools** (test client, assertions) for the actual test logic.

> **Activation:** `/kdx-qa-for-django` or mention by name.

> **BDD FIRST:** Para generación de tests, **SIEMPRE preferir BDD con pytest-bdd**. Usar `kdx-bdd-tests` como skill primario para crear feature files (.feature) y step definitions. Este skill (`kdx-qa-for-django`) se usa para: bug reports, test plans, regression suites, y como referencia de fixtures/assertions. Los tests clásicos (sin .feature) solo se usan para: utilities puras (VPD calculation, DataFrame helpers), model property validation, y performance benchmarks.

## Methodology: Behavior-Driven Development (BDD)

**Primary:** `pytest-bdd` con Gherkin feature files → ver **`kdx-bdd-tests`** para templates completos.

**Secondary (classic):** Para casos simples donde BDD agrega complejidad sin valor. Cada test modela un escenario de usuario usando el patrón **Given / When / Then**:

- **Given (Contexto):** Se establece con fixtures de `conftest.py`. Si toca BD: `@pytest.mark.django_db`.
- **When (Acción):** Se simula con `client.get/post(...)`. Para HTMX: no es necesario header especial (las views de charts usan `csrf_exempt`).
- **Then (Resultado):** Se verifica con assertions de `pytest_django.asserts` (`assertContains`, `assertRedirects`, `assertTemplateUsed`).

### Naming Convention

Class names describe the **user behavior**, not the implementation:

```python
# CORRECTO: describe comportamiento del usuario
class TestUserViewsSensorChart:
class TestSensorDataIngestionViaAPI:
class TestRoomFilterAppliedToSensorList:
class TestVPDPageShowsRoomData:

# INCORRECTO: describe implementación
class TestGenerateSensorView:
class TestDataPointViewSet:
class TestSensorsView:
```

### Test Structure

```python
@pytest.mark.django_db
class TestUserViewsSensorChart:

    def test_chart_returns_html_fragment_for_active_sensor(self, client, sensor_with_data):
        # Given: An active sensor with recent temperature data

        # When: The chart endpoint is called via HTMX POST
        resp = client.post(
            reverse('generate_sensor'),
            {'sensor': sensor_with_data.name, 'timeframe': '4h', 'metric': 't'},
        )

        # Then: The response is an HTML fragment (not a full page)
        assert resp.status_code == 200
        assert b"<!DOCTYPE" not in resp.content
        assert b"<div" in resp.content  # Plotly chart div
```

---

## Stack & Configuration

| Component | Value |
|-----------|-------|
| **Test runner** | pytest 8.3.3 + pytest-django 4.9.0 |
| **Config** | `pytest.ini` → `[pytest]` section |
| **Settings** | `DJANGO_SETTINGS_MODULE = "project.settings"` |
| **Apps** | `core` (Room, Sensor, DataPoint, SiteConfigurations) |

```ini
# pytest.ini (create at project root if not exists)
[pytest]
DJANGO_SETTINGS_MODULE = project.settings
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = --tb=short --strict-markers --no-header -q
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    htmx: marks HTMX endpoint tests
    api: marks DRF API tests
```

---

## Core Concepts: pytest-django

### Database Access is Denied by Default

```python
# Marker on test class (PREFERRED)
@pytest.mark.django_db
class TestUserViewsSensorChart:
    def test_chart_loads(self, client, sensor_with_data):
        ...

# The `db` fixture (for fixtures that need DB access)
@pytest.fixture
def sensor(db):
    room = Room.objects.create(name="Test Room")
    return Sensor.objects.create(name="sensor-01", room=room)
```

**Marker options:**
- `@pytest.mark.django_db` — standard, uses transaction rollback (fast)
- `@pytest.mark.django_db(transaction=True)` — real transactions (slow, needed for testing DB-level constraints)

### pytest-django Fixtures (Built-in)

Do NOT redefine these:

| Fixture | Purpose | Notes |
|---------|---------|-------|
| `client` | `django.test.Client` instance | Fresh per test |
| `admin_client` | Pre-authenticated superuser client | Auto-enables DB |
| `rf` | `django.test.RequestFactory` | For unit-testing views |
| `django_user_model` | Reference to `AUTH_USER_MODEL` | Use instead of importing User |
| `settings` | Django settings with auto-revert | Modify per-test |
| `django_assert_num_queries` | Assert exact query count | Context manager |
| `django_assert_max_num_queries` | Assert max query count | Context manager |
| `db` | Enable DB access for fixtures | Use in custom fixtures |

### Django Assertions (from `pytest_django.asserts`)

```python
from pytest_django.asserts import (
    assertContains,
    assertNotContains,
    assertRedirects,
    assertTemplateUsed,
    assertHTMLEqual,
    assertInHTML,
)
```

---

## Test File Organization

```
core/tests/
├── __init__.py
├── conftest.py                    # Room, Sensor, DataPoint fixtures
├── test_bdd_sensor_charts.py      # BDD: HTMX chart generation behavior
├── test_bdd_api_endpoints.py      # BDD: DRF API behavior
├── test_bdd_room_filtering.py     # BDD: Room/timeframe filter behavior
├── test_views.py                  # Classic: page navigation (home, charts hub)
├── test_models.py                 # Classic: model methods, managers
└── test_utils.py                  # Classic: VPD calc, DataFrame helpers
```

**Rules:**
- Use `tests/` directory under the app (not single `tests.py`)
- One file per concern
- Fixtures that use DB require the `db` fixture parameter
- Test classes use `@pytest.mark.django_db`, NEVER `django.test.TestCase`

---

## Fixtures (conftest.py)

### Core conftest.py

```python
# core/tests/conftest.py
import pytest
from django.utils import timezone
from core.models import Room, Sensor, DataPoint


@pytest.fixture
def room(db):
    return Room.objects.create(name="Test Room")


@pytest.fixture
def sensor(room, db):
    return Sensor.objects.create(name="test-sensor-01", room=room)


@pytest.fixture
def sensor_with_data(sensor, db):
    """20 temperature data points over 4 hours — enough to pass min_points filter."""
    now = timezone.now()
    for i in range(20):
        DataPoint.objects.create(
            sensor=sensor.name,
            metric='t',
            value=20.0 + i * 0.1,
            timestamp=now - timezone.timedelta(hours=4) + timezone.timedelta(minutes=i * 12),
        )
    return sensor


@pytest.fixture
def multi_metric_sensor(sensor, db):
    """Sensor with data for metrics t, h, l, s."""
    now = timezone.now()
    for metric, base_value in [('t', 22.0), ('h', 65.0), ('l', 500.0), ('s', 50.0)]:
        for i in range(20):
            DataPoint.objects.create(
                sensor=sensor.name,
                metric=metric,
                value=base_value + i * 0.1,
                timestamp=now - timezone.timedelta(hours=4) + timezone.timedelta(minutes=i * 12),
            )
    return sensor


@pytest.fixture
def datapoint_factory(db):
    """Factory for DataPoints in specific states."""
    def make(sensor_name, metric='t', value=22.0, hours_ago=1):
        return DataPoint.objects.create(
            sensor=sensor_name,
            metric=metric,
            value=value,
            timestamp=timezone.now() - timezone.timedelta(hours=hours_ago),
        )
    return make
```

---

## Test Patterns

### Comportamiento: Usuario visita una página

```python
# core/tests/test_views.py
import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


@pytest.mark.django_db
class TestUserViewsChartsHub:

    def test_sees_charts_hub_page(self, client):
        # Given: Any user

        # When: Navigates to the charts hub
        resp = client.get(reverse('charts'))

        # Then: Sees the charts page with the correct template
        assert resp.status_code == 200
        assertTemplateUsed(resp, 'charts.html')

    def test_home_page_loads(self, client):
        resp = client.get(reverse('home'))
        assert resp.status_code == 200


@pytest.mark.django_db
class TestUserViewsSensorsPage:

    def test_sensors_page_loads_with_rooms(self, client, room, sensor):
        resp = client.get(reverse('sensors'))
        assert resp.status_code == 200
        assertTemplateUsed(resp, 'charts/sensors.html')

    def test_default_timeframe_is_4h(self, client):
        resp = client.get(reverse('sensors'))
        assert resp.context['timeframe'] == '4h'

    def test_timeframe_param_overrides_default(self, client):
        resp = client.get(reverse('sensors') + '?timeframe=1h')
        assert resp.context['timeframe'] == '1h'
```

### Comportamiento: Usuario genera un gráfico via HTMX

```python
# core/tests/test_views.py
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestUserGeneratesSensorChart:

    def test_chart_returns_html_fragment(self, client, sensor_with_data):
        # Given: Sensor with enough data

        # When: HTMX POST to generate chart
        resp = client.post(
            reverse('generate_sensor'),
            {'sensor': sensor_with_data.name, 'timeframe': '4h', 'metric': 't'},
        )

        # Then: HTML fragment returned (no full page)
        assert resp.status_code == 200
        assert b"<!DOCTYPE" not in resp.content
        assert b"<div" in resp.content

    def test_empty_sensor_returns_no_data_message(self, client, sensor):
        # Given: Sensor with no DataPoints

        # When: Chart generation requested
        resp = client.post(
            reverse('generate_sensor'),
            {'sensor': sensor.name, 'timeframe': '4h', 'metric': 't'},
        )

        # Then: Informative message, not an error
        assert resp.status_code == 200
        assert b"<!DOCTYPE" not in resp.content
        assert b"No hay datos" in resp.content or b"no-data" in resp.content


@pytest.mark.django_db
class TestUserViewsVPDChart:

    def test_vpd_page_loads_with_room_data(self, client, multi_metric_sensor):
        # Given: Sensor with t and h data

        # When: User visits VPD page
        resp = client.get(reverse('vpd'))

        # Then: Page loads with room data for VPD calculation
        assert resp.status_code == 200
        assert 'room_data' in resp.context
```

### Comportamiento: API de ingesta de datos

```python
# core/tests/test_views.py
import pytest
from django.urls import reverse
import json


@pytest.mark.django_db
class TestSensorDataIngestionViaAPI:

    def test_post_datapoint_stores_in_db(self, client):
        # Given: A sensor data payload
        payload = {'sensor': 'sensor-01', 'metric': 't', 'value': 23.5}

        # When: POST to the API
        resp = client.post(
            '/api/data-point/',
            data=json.dumps(payload),
            content_type='application/json',
        )

        # Then: Data point is stored and API returns 201
        assert resp.status_code == 201
        from core.models import DataPoint
        assert DataPoint.objects.filter(sensor='sensor-01', metric='t').exists()

    def test_latest_endpoint_returns_most_recent(self, client, sensor_with_data):
        # Given: Sensor with data

        # When: Request latest data
        resp = client.get(f'/api/data-point/latest/?sensor={sensor_with_data.name}')

        # Then: Returns most recent data point
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert len(data.get('results', [])) > 0
```

### Comportamiento: Lógica de modelos y utilities

```python
# core/tests/test_models.py
import pytest
from core.models import Room, Sensor, DataPoint, SiteConfigurations


@pytest.mark.django_db
class TestSensorBelongsToRoom:

    def test_sensor_str_includes_room_name(self, sensor):
        assert sensor.room.name in str(sensor)

    def test_sensor_deletion_cascades_from_room(self, room, sensor, db):
        room.delete()
        assert not Sensor.objects.filter(pk=sensor.pk).exists()


@pytest.mark.django_db
class TestSiteConfigurationAccess:

    def test_get_all_parameters_returns_dict(self, db):
        SiteConfigurations.objects.create(key="test_key", value="test_value")
        params = SiteConfigurations.get_all_parameters()
        assert params["test_key"] == "test_value"
```

### Comportamiento: Utilities puras (sin BD)

```python
# core/tests/test_utils.py
from core.utils import calculate_vpd, get_timedelta_from_timeframe, calculate_optimal_frequency


class TestVPDCalculation:
    """VPD math — no DB needed."""

    def test_vpd_at_saturation(self):
        # At 100% humidity, VPD should be near 0
        vpd = calculate_vpd(temp=25.0, humidity=100.0)
        assert vpd < 0.1

    def test_vpd_increases_with_temperature(self):
        vpd_low = calculate_vpd(temp=20.0, humidity=60.0)
        vpd_high = calculate_vpd(temp=30.0, humidity=60.0)
        assert vpd_high > vpd_low

    def test_vpd_decreases_with_humidity(self):
        vpd_dry = calculate_vpd(temp=25.0, humidity=40.0)
        vpd_wet = calculate_vpd(temp=25.0, humidity=80.0)
        assert vpd_dry > vpd_wet


class TestTimeframeUtilities:
    """Time range helpers — no DB needed."""

    def test_4h_returns_correct_timedelta(self):
        from datetime import timedelta
        delta = get_timedelta_from_timeframe('4h')
        # 4h * 5x multiplier = 20 hours
        assert delta.total_seconds() == pytest.approx(20 * 3600, rel=0.01)

    def test_optimal_frequency_targets_120_points(self):
        # 4 hours of data, target 120 points → roughly 2-minute intervals
        freq = calculate_optimal_frequency(total_seconds=4*3600, target_points=120)
        assert freq is not None  # Returns a pandas freq string
```

### Performance: Query Count Bounds

```python
@pytest.mark.django_db
class TestSensorsViewQueryPerformance:

    def test_sensors_page_queries_are_bounded(
        self, client, sensor_with_data, django_assert_max_num_queries
    ):
        # Given: A sensor with data

        # When/Then: Page load does not cause unbounded queries
        with django_assert_max_num_queries(20):
            client.get(reverse('sensors'))

    def test_generate_sensor_queries_are_bounded(
        self, client, sensor_with_data, django_assert_max_num_queries
    ):
        with django_assert_max_num_queries(10):
            client.post(
                reverse('generate_sensor'),
                {'sensor': sensor_with_data.name, 'timeframe': '4h', 'metric': 't'},
            )
```

---

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest core/tests/test_views.py

# Specific class
pytest core/tests/test_views.py::TestUserViewsSensorChart

# Specific test
pytest core/tests/test_views.py::TestUserViewsSensorChart::test_chart_returns_html_fragment

# Verbose with output
pytest -v -s

# Stop on first failure
pytest -x

# Skip slow tests
pytest -m "not slow"

# Only HTMX tests
pytest -m "htmx"

# Show slowest tests
pytest --durations=10

# With coverage
pytest --cov=core --cov-report=term-missing
```

---

## What to Test (Priority Order)

### P0 — Core Business Logic & Data Pipeline
- `DataPointDataFrameBuilder.build()` — aggregation and resampling accuracy
- `calculate_vpd()` — formula correctness
- `calculate_optimal_frequency()` — points target math
- `get_active_sensor_names()` — 5x timeframe rule
- `filter_dataframe_by_min_points()` — sparse sensor filtering

### P1 — Views & HTMX Endpoints
- `GenerateSensorView` — chart generation, empty state, HTML fragment
- `GenerateGaugeView` — gauge HTML generation
- `SensorsView` — timeframe/room filtering, context data
- `VPDView` — data aggregation, chart + table
- `InteractiveView` — multi-metric, room grouping

### P2 — DRF API Endpoints
- `DataPointViewSet.latest` — most recent per sensor, time window
- `DataPointViewSet.timeframed` — aggregation by timeframe
- POST to `data-point/` — ingestion with validation
- Metric range validation (t: 2-70, h: 2-100)

### P3 — Edge Cases & Regression
- N+1 queries (`django_assert_max_num_queries`)
- Empty sensor data (no DataPoints) → graceful HTML response
- Sparse sensor data (< 20 points) → filtered from charts
- Invalid timeframe parameters → handled gracefully
- Sensors without room assignment

---

## Bug Report Template

```markdown
# BUG-[ID]: [Core] Descripción clara

**Severidad:** Critical | High | Medium | Low
**Componente:** Model | View | HTMX | API | Utils | Chart

## Entorno
- **Django:** 5.1.3, **Python:** 3.8+
- **Commit:** [hash]
- **URL:** [ruta afectada]

## Pasos para Reproducir
1. [acción]
2. Observar [resultado]

## Esperado vs Real
- **Esperado:** [...]
- **Real:** [...]

## Test de Regresión
```python
@pytest.mark.django_db
class TestBug[ID]:
    def test_[descripción_corta](self, client, sensor_with_data):
        """Regression: [título del bug]."""
        # Given: [contexto que reproduce el bug]
        # When: [acción que dispara el bug]
        # Then: [comportamiento correcto verificado]
```
```

---

## Checklist: Tests para Feature Nueva

1. Fixtures en `conftest.py` — usar `db` fixture, `django_user_model`
2. `@pytest.mark.django_db` en toda clase que toque BD
3. **Nombre de clase = comportamiento del usuario** (`TestUserViewsSensorChart`, no `TestGenerateSensorView`)
4. **Comentarios Given/When/Then** en cada test
5. Model tests: managers, propiedades, cascade deletes
6. View tests: `client` fixture, `assertTemplateUsed`, `assertContains`
7. HTMX tests: verificar `<!DOCTYPE` not in response (es un fragment), verificar contenido del chart
8. API tests: status code, estructura JSON, `DataPoint.objects.filter(...)` para verificar ingesta
9. Utility tests: sin `@pytest.mark.django_db` para lógica pura
10. Performance: `django_assert_max_num_queries` para chart endpoints
11. Negativos: datos vacíos → mensaje informativo, parámetros inválidos → manejo gracioso
