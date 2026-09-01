from unittest.mock import patch
import pytest
from app.models import Comment, db

# ==========================================
# 1. 正常系テスト（各種エンドポイントの呼び出し）
# ==========================================

@patch("app.views.api.register_tasks_by_date")
def test_sync_today_tasks(mock_register, client):
    response = client.get("/api/calendar/sync-tasks/today")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["target_heading"] == "Tasks"
    mock_register.assert_called_once()

@patch("app.views.api.register_tasks_by_date")
def test_sync_tomorrow_tasks(mock_register, client):
    response = client.get("/api/calendar/sync-tasks/tomorrow")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    mock_register.assert_called_once()

@patch("app.views.api.register_tasks_by_date")
def test_sync_tasks_by_date_success(mock_register, client):
    response = client.get("/api/calendar/sync-tasks/date?date=2026-06-01&start_time=10:00")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["date"] == "2026-06-01"
    assert data["start_time"] == "10:00"
    mock_register.assert_called_once()

# 時間帯別のエンドポイントをパラメータライズで効率よくテスト
@pytest.mark.parametrize("endpoint, expected_heading, expected_start", [
    ("/api/calendar/sync-tasks/before-15", "15時まで", "09:00"),
    ("/api/calendar/sync-tasks/before-18", "18時まで", "15:00"),
    ("/api/calendar/sync-tasks/after-18", "18時以降", "18:00"),
])
@patch("app.views.api.register_tasks_by_date")
def test_sync_time_range_tasks(mock_register, client, endpoint, expected_heading, expected_start):
    response = client.get(f"{endpoint}?date=2026-06-01")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["target_heading"] == expected_heading
    assert data["start_time"] == expected_start
    mock_register.assert_called_once()


# ==========================================
# 2. バリデーション・異常系テスト
# ==========================================

def test_sync_tasks_by_date_missing_param(client):
    # dateパラメータが不足している場合 (400)
    response = client.get("/api/calendar/sync-tasks/date")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"

def test_sync_tasks_by_date_invalid_format(client):
    # 日付フォーマットが不正な場合 (400)
    response = client.get("/api/calendar/sync-tasks/date?date=invalid-date")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"


# ==========================================
# 3. サーバーエラー（例外系）テスト
# ==========================================

@patch("app.views.api.register_tasks_by_date", side_effect=Exception("DBまたはファイルエラー"))
def test_sync_tasks_internal_error(mock_register, client):
    # 内部関数で例外が発生した際に 500 が返るか
    response = client.get("/api/calendar/sync-tasks/today")
    assert response.status_code == 500
    data = response.get_json()
    assert data["status"] == "error"
    assert "タスクの同期処理中にエラーが発生しました" in data["message"]


# ==========================================
# 4. コメント関連のテスト
# ==========================================

def test_get_comments(client):
    with client.application.app_context():
        comment = Comment(video_id="test_vid_1", media_type="video", content="テストコメント")
        db.session.add(comment)
        db.session.commit()

    response = client.get("/api/comments/test_vid_1?type=video")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["content"] == "テストコメント"


def test_post_comment(client):
    payload = {"media_type": "video", "content": "新着コメント"}
    response = client.post("/api/comments/test_vid_2", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert "コメントを投稿しました" in data["message"]

    # DBに実際に保存されているか確認
    with client.application.app_context():
        saved = Comment.query.filter_by(video_id="test_vid_2").first()
        assert saved is not None
        assert saved.content == "新着コメント"


def test_update_comment(client):
    with client.application.app_context():
        comment = Comment(video_id="test_vid_3", media_type="video", content="旧コメント")
        db.session.add(comment)
        db.session.commit()
        comment_id = comment.id

    payload = {"content": "更新後コメント"}
    response = client.put(f"/api/comments/{comment_id}", json=payload)
    assert response.status_code == 200
    
    with client.application.app_context():
        updated = Comment.query.get(comment_id)
        assert updated.content == "更新後コメント"


def test_delete_comment(client):
    with client.application.app_context():
        comment = Comment(video_id="test_vid_4", media_type="video", content="削除用コメント")
        db.session.add(comment)
        db.session.commit()
        comment_id = comment.id

    response = client.delete(f"/api/comments/{comment_id}")
    assert response.status_code == 200

    with client.application.app_context():
        deleted = Comment.query.get(comment_id)
        assert deleted is None


@patch("app.views.api.export_today_comments_to_md")
def test_export_comments(mock_export, client):
    response = client.get("/api/comments/export")
    assert response.status_code == 200
    data = response.get_json()
    assert "本日のコメントを出力しました" in data["message"]
    mock_export.assert_called_once()

# ==========================================
# 5. Google Calendar・天気関連のテスト
# ==========================================

@patch("app.views.api.register_today_weather_to_calendar")
def test_register_today_weather(mock_register, client):
    response = client.get("/api/weather/get/today")
    assert response.status_code == 200
    data = response.get_json()
    assert "本日の天気情報をカレンダーに登録しました" in data["message"]
    mock_register.assert_called_once()


@patch("app.views.api.register_tomorrow_weather_to_calendar")
def test_register_tomorrow_weather(mock_register, client):
    response = client.get("/api/weather/get/tomorrow")
    assert response.status_code == 200
    data = response.get_json()
    assert "翌日の天気情報をカレンダーに登録しました" in data["message"]
    mock_register.assert_called_once()

# ==========================================
# 6. Markdown作成関連のテスト
# ==========================================

@patch("app.views.api.create_dailynote")
def test_create_dailynotes_default(mock_create, client):
    # クエリパラメータなし（本日）
    response = client.get("/api/markdown/create_dailynote")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    mock_create.assert_called_once()


@patch("app.views.api.create_dailynote")
def test_create_dailynotes_with_date(mock_create, client):
    # クエリパラメータ指定（YYYY-MM-DD）
    response = client.get("/api/markdown/create_dailynote?start_date=2026-06-01")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["start_date"] == "2026-06-01"
    mock_create.assert_called_once()


def test_create_dailynotes_invalid_date(client):
    # 不正な日付フォーマットの場合 (400)
    response = client.get("/api/markdown/create_dailynote?start_date=invalid-date")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"


@patch("app.views.api.create_weekly_note")
def test_create_weekly_note_success(mock_create, client, monkeypatch):
    # 環境変数を一時的に設定して正常系テスト
    monkeypatch.setenv("WEEKLY_NOTE_DIR", "/dummy/dir")
    monkeypatch.setenv("WEEKLY_NOTE_TEMPLATE", "/dummy/template.md")

    response = client.get("/api/markdown/create_weekly_note?target_date=2026-06-01")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["target_date"] == "2026-06-01"
    mock_create.assert_called_once()


def test_create_weekly_note_missing_env(client, monkeypatch):
    # 環境変数が未設定の場合 (500)
    monkeypatch.delenv("WEEKLY_NOTE_DIR", raising=False)
    monkeypatch.delenv("WEEKLY_NOTE_TEMPLATE", raising=False)

    response = client.get("/api/markdown/create_weekly_note")
    assert response.status_code == 500
    data = response.get_json()
    assert data["status"] == "error"


def test_create_weekly_note_invalid_date(client, monkeypatch):
    # 日付フォーマットが不正な場合 (400)
    monkeypatch.setenv("WEEKLY_NOTE_DIR", "/dummy/dir")
    monkeypatch.setenv("WEEKLY_NOTE_TEMPLATE", "/dummy/template.md")

    response = client.get("/api/markdown/create_weekly_note?target_date=bad-date")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"


@patch("app.views.api.create_next_weekly_note")
def test_create_next_weekly_note_success(mock_create, client):
    response = client.get("/api/markdown/create_next_weekly_note")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "翌週分のウィークリーノートを作成しました" in data["message"]
    mock_create.assert_called_once()
