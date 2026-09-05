from unittest.mock import patch

import pytest

from app.models import Comment, VideoDataModel, MusicDataModel, db


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
@patch("app.views.api.register_tasks_by_date")
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
# 2. バリデーション・異常系テスト
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
# 3. サーバーエラー（例外系）
# ==========================================

@patch(
    "app.views.api.register_tasks_by_date",
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
# 4. コメント関連のテスト
# ==========================================

def test_get_comments(client):
    with client.application.app_context():
        comment = Comment(
            video_id="test_vid_1",
            media_type="video",
            content="テストコメント",
        )

        db.session.add(comment)
        db.session.commit()

    response = client.get(
        "/api/comments/test_vid_1?type=video"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["content"] == "テストコメント"


def test_post_comment(client):
    payload = {
        "media_type": "video",
        "content": "新着コメント",
    }

    response = client.post(
        "/api/comments/test_vid_2",
        json=payload,
    )

    assert response.status_code == 201

    data = response.get_json()

    assert "コメントを投稿しました" in data["message"]

    with client.application.app_context():
        saved = Comment.query.filter_by(
            video_id="test_vid_2"
        ).first()

        assert saved is not None
        assert saved.content == "新着コメント"


def test_update_comment(client):
    with client.application.app_context():
        comment = Comment(
            video_id="test_vid_3",
            media_type="video",
            content="旧コメント",
        )

        db.session.add(comment)
        db.session.commit()

        comment_id = comment.id

    payload = {
        "content": "更新後コメント",
    }

    response = client.put(
        f"/api/comments/{comment_id}",
        json=payload,
    )

    assert response.status_code == 200

    with client.application.app_context():
        updated = Comment.query.get(comment_id)

        assert updated.content == "更新後コメント"


def test_delete_comment(client):
    with client.application.app_context():
        comment = Comment(
            video_id="test_vid_4",
            media_type="video",
            content="削除用コメント",
        )

        db.session.add(comment)
        db.session.commit()

        comment_id = comment.id

    response = client.delete(
        f"/api/comments/{comment_id}"
    )

    assert response.status_code == 200

    with client.application.app_context():
        deleted = Comment.query.get(comment_id)

        assert deleted is None


@patch("app.views.api.export_today_comments_to_md")
def test_export_comments(mock_export, client):
    response = client.get(
        "/api/comments/export"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        "本日のコメントを出力しました"
        in data["message"]
    )

    mock_export.assert_called_once()


# ==========================================
# 5. Google Calendar・天気関連のテスト
# ==========================================

@patch(
    "app.views.api.register_today_weather_to_calendar"
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
    "app.views.api.register_tomorrow_weather_to_calendar"
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


# ==========================================
# 6. Markdown作成関連のテスト
# ==========================================

@patch("app.views.api.create_dailynote")
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


@patch("app.views.api.create_dailynote")
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


@patch("app.views.api.NoteGenerator.create_weekly_note")
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


@patch("app.views.api.create_next_weekly_note")
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
# 7. 動画・音声ストリーミング
# ==========================================

def test_stream_video_success(
    client,
    tmp_path,
):
    video_id = "test_video_01"

    video_dir = tmp_path / "video"
    video_dir.mkdir()

    video_file = video_dir / "test_video.mp4"

    file_content = b"test video content"
    video_file.write_bytes(file_content)

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, video_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        video = VideoDataModel(
            id=video_id,
            new_name="test_video.mp4",
            path=str(video_file),
            original_name="テスト動画",
        )

        db.session.add(video)
        db.session.commit()

    response = client.get(
        f"/api/videos/{video_id}/stream"
    )

    assert response.status_code == 200
    assert response.data == file_content
    assert response.content_length == len(file_content)
    assert response.headers.get("Content-Type") is not None

    with client.application.app_context():
        video = db.session.get(VideoDataModel, video_id)

        if video:
            db.session.delete(video)
            db.session.commit()


def test_stream_video_not_found(client):
    response = client.get(
        "/api/videos/nonexistent_video/stream"
    )

    assert response.status_code == 404


def test_stream_music_success(
    client,
    tmp_path,
):
    music_id = "test_music_01"

    music_dir = tmp_path / "audio"
    music_dir.mkdir()

    music_file = music_dir / "test_music.mp3"

    file_content = b"test music content"
    music_file.write_bytes(file_content)

    with client.application.app_context():
        existing = db.session.get(MusicDataModel, music_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        music = MusicDataModel(
            id=music_id,
            new_name="test_music.mp3",
            path=str(music_file),
            original_name="テスト音声",
        )

        db.session.add(music)
        db.session.commit()

    response = client.get(
        f"/api/musics/{music_id}/stream"
    )

    assert response.status_code == 200
    assert response.data == file_content
    assert response.content_length == len(file_content)
    assert response.headers.get("Content-Type") is not None

    with client.application.app_context():
        music = db.session.get(MusicDataModel, music_id)

        if music:
            db.session.delete(music)
            db.session.commit()


def test_stream_music_not_found(client):
    response = client.get(
        "/api/musics/nonexistent_music/stream"
    )

    assert response.status_code == 404


# ==========================================
# 8. Range Request
# ==========================================

def test_stream_video_range_request(
    client,
    tmp_path,
):
    video_id = "test_range_video"

    video_dir = tmp_path / "video"
    video_dir.mkdir()

    video_file = video_dir / "test_range.mp4"

    file_content = bytes(range(100))
    video_file.write_bytes(file_content)

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, video_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        video = VideoDataModel(
            id=video_id,
            new_name="test_range.mp4",
            path=str(video_file),
            original_name="Rangeテスト動画",
        )

        db.session.add(video)
        db.session.commit()

    response = client.get(
        f"/api/videos/{video_id}/stream",
        headers={
            "Range": "bytes=0-9",
        },
    )

    assert response.status_code == 206
    assert response.data == file_content[:10]
    assert response.content_length == 10
    assert (
        response.headers.get("Content-Range")
        == "bytes 0-9/100"
    )

    with client.application.app_context():
        video = db.session.get(VideoDataModel, video_id)

        if video:
            db.session.delete(video)
            db.session.commit()


def test_stream_music_range_request(
    client,
    tmp_path,
):
    music_id = "test_range_music"

    music_dir = tmp_path / "audio"
    music_dir.mkdir()

    music_file = music_dir / "test_range.mp3"

    file_content = bytes(range(100))
    music_file.write_bytes(file_content)

    with client.application.app_context():
        existing = db.session.get(MusicDataModel, music_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        music = MusicDataModel(
            id=music_id,
            new_name="test_range.mp3",
            path=str(music_file),
            original_name="Rangeテスト音声",
        )

        db.session.add(music)
        db.session.commit()

    response = client.get(
        f"/api/musics/{music_id}/stream",
        headers={
            "Range": "bytes=10-19",
        },
    )

    assert response.status_code == 206
    assert response.data == file_content[10:20]
    assert response.content_length == 10
    assert (
        response.headers.get("Content-Range")
        == "bytes 10-19/100"
    )

    with client.application.app_context():
        music = db.session.get(MusicDataModel, music_id)

        if music:
            db.session.delete(music)
            db.session.commit()
