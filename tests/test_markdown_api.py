from unittest.mock import patch


# ==========================================
# Daily Note
# ==========================================

@patch("app.views.markdown_api.create_dailynote")
def test_create_dailynotes_default(
    mock_create,
    client,
):
    response = client.get(
        "/api/markdown/create_dailynote"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"

    mock_create.assert_called_once()


@patch("app.views.markdown_api.create_dailynote")
def test_create_dailynotes_with_date(
    mock_create,
    client,
):
    response = client.get(
        "/api/markdown/create_dailynote"
        "?start_date=2026-06-01"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["start_date"] == "2026-06-01"

    mock_create.assert_called_once()


def test_create_dailynotes_invalid_date(client):
    response = client.get(
        "/api/markdown/create_dailynote"
        "?start_date=invalid-date"
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["status"] == "error"


# ==========================================
# Weekly Note
# ==========================================

@patch("app.views.markdown_api.NoteGenerator.create_weekly_note")
def test_create_weekly_note_success(
    mock_create,
    client,
    monkeypatch,
):
    monkeypatch.setenv(
        "WEEKLY_NOTE_DIR",
        "/dummy/dir",
    )
    monkeypatch.setenv(
        "WEEKLY_NOTE_TEMPLATE",
        "/dummy/template.md",
    )

    response = client.get(
        "/api/markdown/create_weekly_note"
        "?target_date=2026-06-01"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["target_date"] == "2026-06-01"

    mock_create.assert_called_once()


def test_create_weekly_note_missing_env(
    client,
    monkeypatch,
):
    monkeypatch.delenv(
        "WEEKLY_NOTE_DIR",
        raising=False,
    )
    monkeypatch.delenv(
        "WEEKLY_NOTE_TEMPLATE",
        raising=False,
    )

    response = client.get(
        "/api/markdown/create_weekly_note"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["status"] == "error"


def test_create_weekly_note_invalid_date(
    client,
    monkeypatch,
):
    monkeypatch.setenv(
        "WEEKLY_NOTE_DIR",
        "/dummy/dir",
    )
    monkeypatch.setenv(
        "WEEKLY_NOTE_TEMPLATE",
        "/dummy/template.md",
    )

    response = client.get(
        "/api/markdown/create_weekly_note"
        "?target_date=bad-date"
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["status"] == "error"


# ==========================================
# Next Weekly Note
# ==========================================

@patch("app.views.markdown_api.create_next_weekly_note")
def test_create_next_weekly_note_success(
    mock_create,
    client,
):
    response = client.get(
        "/api/markdown/create_next_weekly_note"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"

    assert (
        "翌週分のウィークリーノートを作成しました"
        in data["message"]
    )

    mock_create.assert_called_once()


# ==========================================
# Vocabulary
# ==========================================

@patch("app.views.markdown_api.export_english_vocabulary")
def test_export_english(
    mock_export,
    client,
):
    response = client.get(
        "/api/markdown/export_english"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == (
        "英単語を出力しました"
    )

    mock_export.assert_called_once()


@patch("app.views.markdown_api.export_single_vocabulary")
def test_export_vocablary(
    mock_export,
    client,
):
    response = client.get(
        "/api/markdown/export_vocablary"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == (
        "語彙を出力しました"
    )

    mock_export.assert_called_once()


# ==========================================
# エラー
# ==========================================

@patch(
    "app.views.markdown_api.create_dailynote",
    side_effect=Exception("daily note error"),
)
def test_create_dailynotes_error(
    mock_create,
    client,
):
    response = client.get(
        "/api/markdown/create_dailynote"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["status"] == "error"
    assert "daily note error" in data["message"]


@patch(
    "app.views.markdown_api.create_next_weekly_note",
    side_effect=Exception("weekly note error"),
)
def test_create_next_weekly_note_error(
    mock_create,
    client,
):
    response = client.get(
        "/api/markdown/create_next_weekly_note"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["status"] == "error"
    assert "weekly note error" in data["message"]
