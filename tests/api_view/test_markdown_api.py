from unittest.mock import patch


def assert_error(response, status_code, fragment=None):
    assert response.status_code == status_code
    payload = response.get_json()
    assert isinstance(payload.get("error"), str)
    if fragment:
        assert fragment.lower() in payload["error"].lower()


def test_create_dailynotes_default(client):
    with patch("app.views.markdown_api.create_dailynote") as create:
        response = client.get("/api/markdown/create_dailynote")

    assert response.status_code == 200
    payload = response.get_json()
    assert "message" in payload
    assert "data" in payload
    assert "start_date" in payload["data"]
    create.assert_called_once()


def test_create_dailynotes_with_date(client):
    with patch("app.views.markdown_api.create_dailynote") as create:
        response = client.get(
            "/api/markdown/create_dailynote",
            query_string={"start_date": "2026-10-12"},
        )

    assert response.status_code == 200
    assert response.get_json()["data"]["start_date"] == "2026-10-12"
    create.assert_called_once()


def test_create_dailynotes_invalid_date(client):
    assert_error(
        client.get("/api/markdown/create_dailynote?start_date=not-a-date"),
        400,
    )


def test_create_dailynotes_error(client):
    with patch(
        "app.views.markdown_api.create_dailynote",
        side_effect=RuntimeError("note creation failed"),
    ):
        response = client.get("/api/markdown/create_dailynote")

    assert_error(response, 500)


def test_create_weekly_note_success(client, monkeypatch):
    monkeypatch.setenv("WEEKLY_NOTE_DIR", "test-weekly-dir")
    monkeypatch.setenv("WEEKLY_NOTE_TEMPLATE", "test-template.md")
    # This endpoint calls NoteGenerator.create_weekly_note directly.
    with patch("app.views.markdown_api.NoteGenerator.create_weekly_note") as create:
        response = client.get(
            "/api/markdown/create_weekly_note",
            query_string={"target_date": "2026-10-12"},
        )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["data"]["target_date"] == "2026-10-12"
    assert "message" in payload
    create.assert_called_once()


def test_create_weekly_note_missing_env(client, monkeypatch):
    monkeypatch.delenv("WEEKLY_NOTE_DIR", raising=False)
    monkeypatch.delenv("WEEKLY_NOTE_TEMPLATE", raising=False)
    response = client.get(
        "/api/markdown/create_weekly_note",
        query_string={"target_date": "2026-10-12"},
    )
    assert_error(response, 500)


def test_create_weekly_note_invalid_date(client):
    assert_error(
        client.get("/api/markdown/create_weekly_note?target_date=not-a-date"),
        400,
    )


def test_create_next_weekly_note_success(client):
    with patch("app.views.markdown_api.create_next_weekly_note"):
        response = client.get("/api/markdown/create_next_weekly_note")

    assert response.status_code == 200
    payload = response.get_json()
    assert "message" in payload
    assert "data" not in payload


def test_create_next_weekly_note_error(client):
    with patch(
        "app.views.markdown_api.create_next_weekly_note",
        side_effect=RuntimeError("weekly note failed"),
    ):
        response = client.get("/api/markdown/create_next_weekly_note")

    assert_error(response, 500)


def test_export_english(client):
    with patch("app.views.markdown_api.export_english_vocabulary"):
        response = client.get("/api/markdown/export_english")

    assert response.status_code == 200
    assert "message" in response.get_json()


def test_export_vocablary(client):
    with patch("app.views.markdown_api.export_single_vocabulary"):
        response = client.get("/api/markdown/export_vocablary")

    assert response.status_code == 200
    assert "message" in response.get_json()


def test_add_thino_summary(client):
    with patch("app.views.markdown_api.add_thino_summary_to_weekly_note"):
        response = client.get("/api/markdown/add_thino_summary")

    assert response.status_code == 200
    assert "message" in response.get_json()


def test_add_thino_summary_by_date(client):
    with patch("app.views.markdown_api.add_thino_summary_to_weekly_note"):
        response = client.get("/api/markdown/add_thino_summary/2026-10-12")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["target_date"] == "2026-10-12"
    assert "message" in payload


def test_add_thino_summary_by_date_invalid(client):
    assert_error(client.get("/api/markdown/add_thino_summary/not-a-date"), 400)
