---
name: kdx-bdd-tests
description: >
  BDD testing skill for this Django project. Generates pytest-bdd feature files,
  step definitions, and test scaffolds following project conventions. Uses Gherkin
  syntax with pytest-django fixtures. Primary testing methodology — all test
  generation MUST use BDD patterns first.
trigger: explicit
---

# BDD Tests (kdx-bdd-tests)

Primary testing skill for this Django project. **All tests MUST follow BDD methodology** using `pytest-bdd` with Gherkin feature files and Python step definitions integrated with `pytest-django`.

> **Activation:** `/kdx-bdd-tests` or mention by name.
> **Priority:** This skill takes precedence over `kdx-qa-for-django` for test generation. Use `kdx-qa-for-django` for bug reports and non-BDD utilities.

> **Prerequisite:** Add `pytest-bdd>=8.0` to `requirements.txt` before writing BDD tests.

---

## Architecture

```
features/                              # Gherkin feature files (bdd_features_base_dir)
└── core/                              # Per-app subdirectory
    ├── sensor_charts.feature          # Feature: HTMX chart generation
    ├── api_endpoints.feature          # Feature: DRF API data access
    ├── data_ingestion.feature         # Feature: DataPoint write operations
    ├── room_filtering.feature         # Feature: Room/sensor filter behavior
    └── vpd_calculation.feature        # Feature: VPD computation and display

core/tests/                            # Step definitions + classic tests
├── conftest.py                        # Shared fixtures (Room, Sensor, DataPoint factories)
├── test_bdd_sensor_charts.py          # Steps for sensor_charts.feature
├── test_bdd_api_endpoints.py          # Steps for api_endpoints.feature
├── test_bdd_data_ingestion.py         # Steps for data_ingestion.feature
├── test_bdd_room_filtering.py         # Steps for room_filtering.feature
└── test_models.py                     # Classic tests (pure model logic, no user context)
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Feature file | `snake_case.feature` | `sensor_charts.feature` |
| Step definition file | `test_bdd_<feature>.py` | `test_bdd_sensor_charts.py` |
| Feature title | User behavior | `Feature: Sensor Chart Generation` |
| Scenario title | Specific outcome | `Scenario: Chart loads for active sensor` |
| Tags | `@core`, `@htmx`, `@api`, `@slow` | `@core @htmx` |

---

## Stack & Configuration

| Component | Version | Purpose |
|-----------|---------|---------|
| **pytest-bdd** | 8.x | BDD framework with Gherkin parser |
| **pytest** | 8.3.3 | Test runner |
| **pytest-django** | 4.9.0 | Django integration, DB access, fixtures |

### pytest.ini Configuration

Create `pytest.ini` in the project root (the project has no `pyproject.toml`):

```ini
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
    core: marks core app tests
bdd_features_base_dir = features/
```

**Test mode detection** (add to `project/settings.py` if not present):
```python
import sys
TESTING = 'test' in sys.argv or any('pytest' in arg for arg in sys.argv)
```
When `TESTING` is true: optionally use SQLite in-memory for speed.

---

## Feature File Patterns

### HTMX Chart Feature

```gherkin
@core @htmx
Feature: Sensor Chart Generation
    As a monitoring user
    I want to view sensor charts by timeframe
    So that I can analyze environmental data trends

    Background:
        Given a room "Grow Room A" with sensor "sensor-01"
        And the sensor has 15 temperature data points in the last 4 hours

    Scenario: Chart loads for active sensor
        When the user requests a chart for sensor "sensor-01" timeframe "4h" metric "t"
        Then the response is an HTML fragment
        And the response contains a Plotly chart

    Scenario: Empty state for sensor with no data
        Given a sensor "empty-sensor" with no data
        When the user requests a chart for sensor "empty-sensor" timeframe "1h" metric "t"
        Then the response shows a no-data message

    Scenario: Chart generation respects minimum data threshold
        Given a sensor "sparse-sensor" with only 5 data points
        When the user requests a chart for sensor "sparse-sensor" timeframe "4h" metric "t"
        Then the response shows a no-data message
```

### API Endpoint Feature

```gherkin
@core @api
Feature: DataPoint API Endpoints
    As an IoT device or monitoring client
    I want to read and write sensor data via the API
    So that I can ingest and analyze environmental measurements

    Scenario: Ingest a temperature data point
        When a sensor posts temperature 23.5 for sensor "sensor-01"
        Then the data point is stored in the database
        And the API returns status 201

    Scenario: Fetch latest data returns most recent reading
        Given sensor "sensor-01" has temperature readings over the last hour
        When the client requests the latest data for sensor "sensor-01"
        Then the response contains the most recent temperature value
        And the response status is 200

    Scenario: Timeframed data returns aggregated readings
        Given sensor "sensor-01" has 60 temperature readings over 1 hour
        When the client requests timeframed data for sensor "sensor-01" with timeframe "1h"
        Then the response contains aggregated data points
        And the number of data points is less than 60
```

### Room Filtering Feature

```gherkin
@core
Feature: Room-Based Sensor Filtering
    As a monitoring user
    I want to filter charts by room
    So that I can focus on a specific growing area

    Scenario: Sensors view defaults to all rooms
        Given rooms "Room A" and "Room B" each with one sensor
        When the user visits the sensors page without a room filter
        Then sensors from both rooms are displayed

    Scenario: Room filter shows only that room's sensors
        Given rooms "Room A" and "Room B" each with one sensor
        When the user filters by room "Room A"
        Then only Room A sensors are displayed
        And Room B sensors are not displayed

    Scenario Outline: Access control by URL
        When the user visits "<url>"
        Then the response status is <status>

        Examples:
            | url              | status |
            | /charts/         | 200    |
            | /charts/sensors/ | 200    |
            | /charts/vpd/     | 200    |
            | /charts/gauges/  | 200    |
```

---

## Step Definition Patterns

### Basic Structure

```python
"""Step definitions for sensor_charts.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from django.urls import reverse
from django.utils import timezone
from core.models import Room, Sensor, DataPoint

# Collect all scenarios from the feature file
scenarios("core/sensor_charts.feature")

# All steps in this module need DB access
pytestmark = pytest.mark.django_db


# --- GIVEN: Setup (reuse conftest.py fixtures) ---

@given(parsers.parse('a room "{room_name}" with sensor "{sensor_name}"'),
       target_fixture="sensor")
def create_room_sensor(room_name, sensor_name, db):
    room = Room.objects.create(name=room_name)
    return Sensor.objects.create(name=sensor_name, room=room)


@given(parsers.parse('the sensor has {count:d} temperature data points in the last {hours:d} hours'))
def create_sensor_data(sensor, count, hours, db):
    now = timezone.now()
    interval = hours / count
    for i in range(count):
        DataPoint.objects.create(
            sensor=sensor.name,
            metric='t',
            value=20.0 + i * 0.2,
            timestamp=now - timezone.timedelta(hours=hours - i * interval),
        )


@given(parsers.parse('a sensor "{sensor_name}" with no data'), target_fixture="empty_sensor")
def empty_sensor(sensor_name, db):
    room = Room.objects.create(name="Empty Room")
    return Sensor.objects.create(name=sensor_name, room=room)


# --- WHEN: Actions ---

@when(parsers.parse('the user requests a chart for sensor "{sensor_name}" timeframe "{timeframe}" metric "{metric}"'),
      target_fixture="response")
def request_chart(client, sensor_name, timeframe, metric):
    return client.post(
        reverse('generate_sensor'),
        {'sensor': sensor_name, 'timeframe': timeframe, 'metric': metric},
    )


# --- THEN: Assertions ---

@then("the response is an HTML fragment")
def is_html_fragment(response):
    assert response.status_code == 200
    assert b"<!DOCTYPE" not in response.content


@then("the response contains a Plotly chart")
def has_plotly_chart(response):
    assert b"plotly" in response.content.lower() or b"<div" in response.content


@then("the response shows a no-data message")
def no_data_message(response):
    assert response.status_code == 200
    assert b"no-data" in response.content or b"No hay datos" in response.content or b"no data" in response.content.lower()
```

### Fixture Bridge Pattern

Steps bridge Gherkin to existing conftest.py fixtures using `target_fixture`:

```python
@given("an active sensor with recent data", target_fixture="active_sensor")
def _(sensor_with_data):
    """Reuses the sensor_with_data fixture from conftest.py."""
    return sensor_with_data


@given("a room with multiple sensors", target_fixture="multi_sensor_room")
def _(room_factory):
    return room_factory(sensor_count=3)
```

### Parsers for Dynamic Values

```python
from pytest_bdd import parsers

@given(parsers.parse('a sensor posts temperature {value:f} for sensor "{sensor_name}"'),
       target_fixture="ingest_response")
def post_datapoint(client, value, sensor_name):
    return client.post(
        '/api/data-point/',
        {'sensor': sensor_name, 'metric': 't', 'value': value},
        content_type='application/json',
    )


@then(parsers.parse("the response status is {code:d}"))
def check_status_code(response, code):
    assert response.status_code == code


@then(parsers.parse('the response contains aggregated data points'))
def has_data_points(response):
    import json
    data = json.loads(response.content)
    assert len(data.get('results', [])) > 0
```

---

## Integration with Existing Fixtures

### conftest.py Fixtures (DO NOT REDEFINE)

**pytest-django (built-in):**
- `client` — `django.test.Client` instance (fresh per test)
- `rf` — `django.test.RequestFactory`
- `django_user_model` — Reference to `AUTH_USER_MODEL`
- `settings` — Django settings with auto-revert
- `db`, `django_assert_num_queries`, `django_assert_max_num_queries`

**Project-specific (add to `core/tests/conftest.py`):**

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
    """Sensor with 20 temperature data points over the last 4 hours."""
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
def datapoint_factory(db):
    """Factory for creating DataPoints in specific states."""
    def make_datapoint(sensor_name, metric='t', value=22.0, hours_ago=1):
        return DataPoint.objects.create(
            sensor=sensor_name,
            metric=metric,
            value=value,
            timestamp=timezone.now() - timezone.timedelta(hours=hours_ago),
        )
    return make_datapoint


@pytest.fixture
def room_factory(db):
    """Factory for creating rooms with multiple sensors."""
    def make_room(name="Factory Room", sensor_count=1):
        room = Room.objects.create(name=name)
        sensors = [
            Sensor.objects.create(name=f"sensor-{i+1:02d}", room=room)
            for i in range(sensor_count)
        ]
        return room, sensors
    return make_room
```

### Rule: Steps Are Thin Adapters

Steps should **only** orchestrate existing fixtures, not duplicate their logic:

```python
# CORRECT: Reuses conftest fixtures
@given("a sensor with recent data", target_fixture="ready_sensor")
def _(sensor_with_data):
    return sensor_with_data

# INCORRECT: Duplicates conftest logic
@given("a sensor with recent data", target_fixture="ready_sensor")
def _(db):
    room = Room.objects.create(...)
    sensor = Sensor.objects.create(...)
    # ... 15 more lines that conftest already handles
```

---

## HTMX-Specific BDD Patterns

### HTMX Request Simulation

```python
@when("the user requests chart content via HTMX", target_fixture="response")
def htmx_chart_request(client, sensor):
    return client.post(
        reverse('generate_sensor'),
        {'sensor': sensor.name, 'timeframe': '4h', 'metric': 't'},
        # Note: GenerateSensorView is csrf_exempt, no headers needed
    )
```

### HTMX Response Assertions

```python
@then("the response is an HTML partial")
def html_partial(response):
    assert response.status_code == 200
    assert b"<!DOCTYPE" not in response.content  # Not a full page

@then("the chart HTML is injected")
def chart_injected(response):
    assert b"<div" in response.content  # Plotly div present
    assert b"plotly" in response.content.lower()

@then("the server responds with status 200")
def status_ok(response):
    assert response.status_code == 200
```

---

## Running BDD Tests

```bash
# Install pytest-bdd first
pip install pytest-bdd>=8.0

# All BDD tests
pytest --co -q  # List collected scenarios

# All tests (BDD + classic)
pytest

# Only BDD tests from a specific feature
pytest core/tests/test_bdd_sensor_charts.py

# By tag
pytest -m "htmx"
pytest -m "api"
pytest -m "core and not slow"

# Verbose with scenario names
pytest -v core/tests/test_bdd_sensor_charts.py

# Generate missing step stubs (dry run)
pytest --generate-missing core/tests/test_bdd_sensor_charts.py

# Stop on first failure
pytest -x

# Show slowest tests
pytest --durations=10
```

---

## Workflow: Creating BDD Tests for a New Feature

### 1. Write the Feature File

```bash
mkdir -p features/core/
# Create features/core/<feature_name>.feature
```

Write scenarios from the user's perspective. Use `Background` for shared setup.

### 2. Create Step Definition File

```bash
mkdir -p core/tests/
# Create core/tests/test_bdd_<feature_name>.py
```

Start with:
```python
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from django.urls import reverse

scenarios("core/<feature_name>.feature")

pytestmark = pytest.mark.django_db
```

### 3. Implement Steps

- **Given** → Bridge to conftest.py fixtures via `target_fixture`
- **When** → Simulate user actions via `client` (GET/POST)
- **Then** → Assert on response, database state

### 4. Run and Iterate

```bash
pytest core/tests/test_bdd_<feature_name>.py -v
```

Use `--generate-missing` to see which steps need implementation.

---

## When to Use BDD vs Classic Tests

| Use BDD (pytest-bdd) | Use Classic (pytest) |
|---|---|
| User-facing behavior | Pure unit logic (no user context) |
| HTMX chart loading | DataPoint model validation |
| API endpoint behavior | Utility function math (VPD calc) |
| Room/timeframe filtering | DataFrame aggregation helpers |
| Data ingestion via API | Pure model property tests |

**Default is BDD.** Classic tests are the exception.

---

## Tags Reference

| Tag | Meaning | pytest marker |
|-----|---------|---------------|
| `@core` | Core app tests | `-m core` |
| `@htmx` | HTMX endpoint tests | `-m htmx` |
| `@api` | DRF API tests | `-m api` |
| `@slow` | Long-running tests | `-m slow` |
| `@wip` | Work in progress | `-m wip` |

---

## Checklist: New BDD Test

1. Feature file in `features/core/` — Gherkin, user perspective
2. Step file as `core/tests/test_bdd_<feature>.py`
3. `scenarios()` call links to feature file
4. `pytestmark = pytest.mark.django_db` if any step touches DB
5. Given steps reuse conftest.py fixtures via `target_fixture`
6. When steps simulate user actions (client GET/POST)
7. Then steps assert response status, content, DB state
8. HTMX endpoints: verify `<!DOCTYPE` not in response (it's a partial)
9. No implementation details in feature files
10. Run `pytest -v core/tests/test_bdd_<feature>.py` to verify
