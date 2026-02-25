---
name: bdd-patterns
user-invocable: false
description: BDD patterns with pytest-bdd for this Django project. Provides Gherkin feature file structure, step definitions with pytest-django fixtures, and Given-When-Then patterns integrated with the project's testing stack.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# BDD Patterns (pytest-bdd + Django)

Behavior-Driven Development patterns using **pytest-bdd 8.x** with **pytest-django**. Feature files use Gherkin syntax; step definitions are pure Python functions integrated with the project's fixture ecosystem.

## Stack

| Component | Version |
|-----------|---------|
| **pytest-bdd** | 8.x |
| **pytest** | 8.3.3 |
| **pytest-django** | 4.9.0 |
| **Gherkin** | Standard syntax via `gherkin-official` |

> **Note**: pytest-bdd is not in requirements.txt by default. Add `pytest-bdd>=8.0` to requirements.txt before using BDD tests.

## Project Convention

```
features/                              # bdd_features_base_dir (pytest.ini)
└── core/                              # Per-app feature files
    ├── sensor_charts.feature          # HTMX chart generation behavior
    ├── api_endpoints.feature          # DRF API behavior
    ├── data_ingestion.feature         # DataPoint write behavior
    └── room_filtering.feature         # Room/sensor filtering behavior

core/tests/                            # Step definitions colocated with tests
├── conftest.py                        # Shared fixtures (existing)
├── test_bdd_sensor_charts.py          # Steps for sensor_charts.feature
├── test_bdd_api_endpoints.py          # Steps for api_endpoints.feature
└── test_bdd_data_ingestion.py         # Steps for data_ingestion.feature
```

### pytest.ini Configuration

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
bdd_features_base_dir = features/
```

---

## Given-When-Then Structure

The fundamental BDD pattern:

- **Given**: Preconditions — set up via pytest fixtures and step functions
- **When**: Action — user interaction simulated via Django test client or API call
- **Then**: Outcome — assertions on response, database state, chart content

---

## Feature File Syntax (Gherkin)

```gherkin
@core @htmx
Feature: Sensor Chart Generation
    As a monitoring user
    I want to view sensor charts by timeframe
    So that I can analyze environmental data over time

    Background:
        Given a room "Grow Room A" with sensor "sensor-01"
        And the sensor has temperature data in the last 4 hours

    Scenario: Generate sensor chart via HTMX
        When the user requests a chart for sensor "sensor-01" with timeframe "4h"
        Then the response contains a Plotly chart
        And the response is an HTML fragment

    Scenario: No data returns empty state message
        Given a sensor "sensor-empty" with no data
        When the user requests a chart for sensor "sensor-empty" with timeframe "1h"
        Then the response contains a no-data message

    Scenario Outline: Chart generation by timeframe
        When the user requests a chart for timeframe "<timeframe>"
        Then the chart is generated successfully

        Examples:
            | timeframe |
            | 1min      |
            | 30min     |
            | 1h        |
            | 4h        |
            | 1d        |
```

---

## Step Definitions (pytest-bdd + pytest-django)

```python
# core/tests/test_bdd_sensor_charts.py
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from django.urls import reverse
from django.utils import timezone
from core.models import Room, Sensor, DataPoint

# Link feature file
scenarios("core/sensor_charts.feature")

# All steps need DB access
pytestmark = pytest.mark.django_db


# --- Given steps ---

@given(parsers.parse('a room "{room_name}" with sensor "{sensor_name}"'),
       target_fixture="sensor")
def room_and_sensor(room_name, sensor_name, db):
    room = Room.objects.create(name=room_name)
    return Sensor.objects.create(name=sensor_name, room=room)


@given(parsers.parse('the sensor has temperature data in the last {hours:d} hours'))
def sensor_has_data(sensor, hours, db):
    now = timezone.now()
    for i in range(10):
        DataPoint.objects.create(
            sensor=sensor.name,
            metric='t',
            value=22.0 + i * 0.1,
            timestamp=now - timezone.timedelta(hours=hours - i * (hours / 10)),
        )


# --- When steps ---

@when(parsers.parse('the user requests a chart for sensor "{sensor_name}" with timeframe "{timeframe}"'),
      target_fixture="response")
def request_sensor_chart(client, sensor_name, timeframe):
    return client.post(
        reverse('generate_sensor'),
        {'sensor': sensor_name, 'timeframe': timeframe, 'metric': 't'},
    )


# --- Then steps ---

@then("the response contains a Plotly chart")
def response_has_plotly(response):
    assert response.status_code == 200
    assert b"plotly" in response.content.lower() or b"<div" in response.content


@then("the response is an HTML fragment")
def response_is_fragment(response):
    assert response.status_code == 200
    assert b"<!DOCTYPE" not in response.content


@then("the response contains a no-data message")
def response_has_no_data(response):
    assert response.status_code == 200
    assert b"no-data" in response.content or b"No hay datos" in response.content
```

---

## Key Patterns

### 1. Linking Scenarios to Feature Files

```python
from pytest_bdd import scenarios

# All scenarios from a feature file
scenarios("core/sensor_charts.feature")

# Or specific scenario
from pytest_bdd import scenario

@scenario("core/sensor_charts.feature", "Generate sensor chart via HTMX")
def test_generate_chart():
    pass
```

### 2. Reusing pytest-django Fixtures in Steps

```python
@given("a room with active sensors", target_fixture="room_with_sensors")
def _(db, django_user_model):
    """Create Room + Sensor + DataPoints via fixtures."""
    room = Room.objects.create(name="Test Room")
    sensor = Sensor.objects.create(name="test-sensor", room=room)
    return room, sensor
```

### 3. Parametrized Scenarios (Scenario Outline)

```gherkin
Scenario Outline: API endpoint returns data for metric
    When the client requests latest data for metric "<metric>"
    Then the response status is <status>

    Examples:
        | metric | status |
        | t      | 200    |
        | h      | 200    |
        | x      | 400    |
```

```python
@when(parsers.parse('the client requests latest data for metric "{metric}"'),
      target_fixture="response")
def request_metric(client, metric):
    return client.get(f'/api/data-point/latest/?metric={metric}')


@then(parsers.parse("the response status is {status:d}"))
def check_status(response, status):
    assert response.status_code == status
```

### 4. Database Access

pytest-bdd inherits pytest-django's DB rules. Steps that need DB must have fixtures with `db` dependency or use the marker:

```python
# Mark all BDD tests in the module that need DB
pytestmark = pytest.mark.django_db
```

---

## Best Practices

- **Feature files** describe WHAT (user behavior), not HOW (implementation)
- **Step definitions** are thin adapters between Gherkin and existing fixtures
- **Reuse** existing conftest.py fixtures — don't duplicate setup in steps
- **One feature** per `.feature` file, organized by domain
- **Background** for shared preconditions within a feature
- **Tags** (`@slow`, `@htmx`, `@core`) map to pytest markers
- **Declarative language** — "the user views the sensors chart" not "GET /charts/sensors/"

## Common Pitfalls

- Forgetting `@pytest.mark.django_db` on step definition modules
- Not using `target_fixture` to pass state between Given → When → Then
- Writing step definitions that duplicate fixture logic
- Over-specifying implementation in feature files
- Not linking `scenarios()` call — scenarios won't be collected
- Using `csrf_exempt` in views but forgetting HTMX request headers in tests
