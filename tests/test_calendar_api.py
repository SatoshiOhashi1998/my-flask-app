from unittest.mock import patch

import pytest


# ==========================================
# タスク同期
# ==========================================

@patch("app.views.calendar_api.register_tasks_by_date")
def test_sync_today_tasks(mock_register, client):
    response = client.get("/api/calendar/sync-tasks/today")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["target_heading"] == "Today's Tasks"

    mock_register.assert_called_once()


@patch("app.views.calendar_api.register_tasks_by_date")
def test_sync_tomorrow_tasks(mock_register, client):
    response = client.get("/api/calendar/sync-tasks/tomorrow")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"

    mock_register.assert_called_once()


@patch("app.views.calendar_api.register_tasks_by_date")
def test_sync_tasks_by_date_success(mock_register, client):
    response = client.get(
        "/api/calendar/sync-tasks/date"
        "?date=2026-06-01&start_time=10:00"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["date"] == "2026-06-01"
    assert data["start_time"] == "10:00"

    mock_register.assert_called_once()


@pytest.mark.parametrize(
    "endpoint, expected_heading, expected_start",
    [
        (
            "/api/calendar/sync-tasks/before-15",
            "15時まで",
            "09:00",
        ),
        (
            "/api/calendar/sync-tasks/before-18",
            "18時まで",
            "15:00",
        ),
        (
            "/api/calendar/sync-tasks/after-18",
            "18時以降",
            "18:00",
        ),
    ],
)
@patch("app.views.calendar_api.register_tasks_by_date")
def test_sync_time_range_tasks(
    mock_register,
    client,
    endpoint,
    expected_heading,
    expected_start,
):
    response = client.get(
        f"{endpoint}?date=2026-06-01"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["target_heading"] == expected_heading
    assert data["start_time"] == expected_start

    mock_register.assert_called_once()


# ==========================================
# バリデーション
# ==========================================

def test_sync_tasks_by_date_missing_param(client):
    response = client.get(
        "/api/calendar/sync-tasks/date"
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["status"] == "error"


def test_sync_tasks_by_date_invalid_format(client):
    response = client.get(
        "/api/calendar/sync-tasks/date"
        "?date=invalid-date"
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["status"] == "error"


# ==========================================
# エラー
# ==========================================

@patch(
    "app.views.calendar_api.register_tasks_by_date",
    side_effect=Exception("DBまたはファイルエラー"),
)
def test_sync_tasks_internal_error(
    mock_register,
    client,
):
    response = client.get(
        "/api/calendar/sync-tasks/today"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["status"] == "error"
    assert (
        "タスクの同期処理中にエラーが発生しました"
        in data["message"]
    )


# ==========================================
# 天気
# ==========================================

@patch(
    "app.views.calendar_api.register_today_weather_to_calendar"
)
def test_register_today_weather(
    mock_register,
    client,
):
    response = client.get(
        "/api/weather/get/today"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        "本日の天気情報をカレンダーに登録しました"
        in data["message"]
    )

    mock_register.assert_called_once()


@patch(
    "app.views.calendar_api.register_tomorrow_weather_to_calendar"
)
def test_register_tomorrow_weather(
    mock_register,
    client,
):
    response = client.get(
        "/api/weather/get/tomorrow"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        "翌日の天気情報をカレンダーに登録しました"
        in data["message"]
    )

    mock_register.assert_called_once()


@patch(
    "app.views.calendar_api.register_today_weather_to_calendar",
    side_effect=Exception("weather error"),
)
def test_register_today_weather_error(
    mock_register,
    client,
):
    response = client.get(
        "/api/weather/get/today"
    )

    assert response.status_code == 500


@patch(
    "app.views.calendar_api.register_tomorrow_weather_to_calendar",
    side_effect=Exception("weather error"),
)
def test_register_tomorrow_weather_error(
    mock_register,
    client,
):
    response = client.get(
        "/api/weather/get/tomorrow"
    )

    assert response.status_code == 500
