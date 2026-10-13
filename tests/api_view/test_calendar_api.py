from unittest.mock import patch

import pytest


def assert_error(response, status_code, fragment=None):
    assert response.status_code == status_code
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert isinstance(payload.get("error"), str)
    if fragment:
        assert fragment.lower() in payload["error"].lower()


@pytest.mark.parametrize(
    ("endpoint", "expected_start_time", "expected_heading"),
    [
        ("/api/calendar/sync-tasks/before-15", "09:00", "15時まで"),
        ("/api/calendar/sync-tasks/before-18", "15:00", "18時まで"),
        ("/api/calendar/sync-tasks/after-18", "18:00", "18時以降"),
    ],
)
def test_sync_time_range_tasks(client, endpoint, expected_start_time, expected_heading):
    with patch("app.views.calendar_api.register_tasks_by_date") as register:
        response = client.get(endpoint)

    assert response.status_code == 200
    payload = response.get_json()
    assert "data" in payload
    assert payload["data"]["start_time"] == expected_start_time
    assert payload["data"]["target_heading"] == expected_heading
    assert "message" in payload
    register.assert_called_once()


def test_sync_tasks_by_date_success(client):
    with patch("app.views.calendar_api.register_tasks_by_date") as register:
        response = client.get("/api/calendar/sync-tasks/date?date=2026-10-12")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["date"] == "2026-10-12"
    assert "message" in payload
    register.assert_called_once()


def test_sync_tasks_by_date_missing_param(client):
    assert_error(client.get("/api/calendar/sync-tasks/date"), 400)


@pytest.mark.parametrize("date_value", ["12-10-2026", "not-a-date", "2026-13-40"])
def test_sync_tasks_by_date_invalid_format(client, date_value):
    response = client.get(
        "/api/calendar/sync-tasks/date",
        query_string={"date": date_value},
    )
    assert_error(response, 400)


def test_sync_tasks_internal_error(client):
    with patch(
        "app.views.calendar_api.register_tasks_by_date",
        side_effect=RuntimeError("calendar backend failed"),
    ):
        response = client.get("/api/calendar/sync-tasks/date?date=2026-10-12")

    assert_error(response, 500)


@pytest.mark.parametrize(
    "endpoint",
    ["/api/weather/get/today", "/api/weather/get/tomorrow"],
)
def test_register_weather_success(client, endpoint):
    # The weather route's success response is message-only by contract.
    response = client.get(endpoint)
    assert response.status_code == 200
    payload = response.get_json()
    assert "message" in payload
    assert "data" not in payload
    assert "error" not in payload
