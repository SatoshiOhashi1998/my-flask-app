from unittest.mock import patch
import locale
import pytest

from app.models import Comment, VideoDataModel, MusicDataModel, db
from app.utils import MEDIA_BASE_PATHS


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

# ==========================================
# 9. 動画・音楽一覧 / info API
# ==========================================

@patch("app.views.api.locale.setlocale")
def test_get_videos(mock_setlocale, client, tmp_path):
    with client.application.app_context():
        video1 = VideoDataModel(
            id="video_01",
            new_name="video_01.mp4",
            path=str(tmp_path / "video" / "video_01.mp4"),
            original_name="動画1",
        )

        video2 = VideoDataModel(
            id="video_02",
            new_name="video_02.mp4",
            path=str(tmp_path / "video" / "video_02.mp4"),
            original_name="動画2",
        )

        db.session.add_all([video1, video2])
        db.session.commit()

    response = client.get("/api/videos")

    assert response.status_code == 200

    data = response.get_json()

    assert "items" in data
    assert len(data["items"]) == 2

    assert data["items"][0]["type"] == "video"
    assert data["items"][0]["filename"] == "video_01.mp4"

    mock_setlocale.assert_called_once_with(
        locale.LC_COLLATE,
        "ja_JP.UTF-8",
    )


def test_get_video_info(client, tmp_path):
    video_id = "video_info_01"

    with client.application.app_context():
        video = VideoDataModel(
            id=video_id,
            new_name="sample.mp4",
            path=str(tmp_path / "video" / "sample.mp4"),
            original_name="サンプル動画",
        )

        db.session.add(video)
        db.session.commit()

    response = client.get(
        f"/api/videos/{video_id}/info"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == "sample"
    assert data["filename"] == "sample.mp4"
    assert data["filetitle"] == "サンプル動画"
    assert data["type"] == "video"


def test_get_video_info_not_found(client):
    response = client.get(
        "/api/videos/nonexistent_video/info"
    )

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Video not found"


@patch("app.views.api.locale.setlocale")
def test_get_musics(mock_setlocale, client, tmp_path):
    with client.application.app_context():
        music1 = MusicDataModel(
            id="music_01",
            new_name="music_01.mp3",
            path=str(tmp_path / "audio" / "music_01.mp3"),
            original_name="音楽1",
        )

        music2 = MusicDataModel(
            id="music_02",
            new_name="music_02.mp3",
            path=str(tmp_path / "audio" / "music_02.mp3"),
            original_name="音楽2",
        )

        db.session.add_all([music1, music2])
        db.session.commit()

    response = client.get("/api/musics")

    assert response.status_code == 200

    data = response.get_json()

    assert "items" in data
    assert len(data["items"]) == 2

    assert data["items"][0]["type"] == "audio"
    assert data["items"][0]["filename"] == "music_01.mp3"

    mock_setlocale.assert_called_once_with(
        locale.LC_COLLATE,
        "ja_JP.UTF-8",
    )


def test_get_music_info(client, tmp_path):
    music_id = "music_info_01"

    with client.application.app_context():
        music = MusicDataModel(
            id=music_id,
            new_name="sample.mp3",
            path=str(tmp_path / "audio" / "sample.mp3"),
            original_name="サンプル音声",
        )

        db.session.add(music)
        db.session.commit()

    response = client.get(
        f"/api/musics/{music_id}/info"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == "sample"
    assert data["filename"] == "sample.mp3"
    assert data["filetitle"] == "サンプル音声"
    assert data["type"] == "audio"


def test_get_music_info_not_found(client):
    response = client.get(
        "/api/musics/nonexistent_music/info"
    )

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Music not found"

# ==========================================
# 10. コメントその他
# ==========================================

def test_get_other_comments(client):
    with client.application.app_context():
        comments = [
            Comment(
                video_id="test_other_01",
                media_type="youtube",
                content="YouTubeコメント",
            ),
            Comment(
                video_id="test_other_01",
                media_type="video",
                content="動画コメント",
            ),
            Comment(
                video_id="test_other_01",
                media_type="audio",
                content="音声コメント",
            ),
        ]

        db.session.add_all(comments)
        db.session.commit()

    response = client.get(
        "/api/comments/test_other_01/others"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 2

    media_types = {
        comment["media_type"]
        for comment in data
    }

    assert "youtube" not in media_types
    assert "video" in media_types
    assert "audio" in media_types


def test_get_other_comments_custom_exclude_type(client):
    with client.application.app_context():
        comments = [
            Comment(
                video_id="test_other_02",
                media_type="youtube",
                content="YouTubeコメント",
            ),
            Comment(
                video_id="test_other_02",
                media_type="video",
                content="動画コメント",
            ),
        ]

        db.session.add_all(comments)
        db.session.commit()

    response = client.get(
        "/api/comments/test_other_02/others"
        "?exclude_type=video"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["media_type"] == "youtube"


def test_update_comment_not_found(client):
    response = client.put(
        "/api/comments/999999",
        json={
            "content": "更新",
        },
    )

    assert response.status_code == 404


def test_delete_comment_not_found(client):
    response = client.delete(
        "/api/comments/999999"
    )

    assert response.status_code == 404

# ==========================================
# 11. YouTube ダウンロード API
# ==========================================

@patch("app.views.api.get_media_directories")
def test_youtube_download_get(
    mock_get_directories,
    client,
):
    mock_get_directories.return_value = [
        "D:/media/video",
        "D:/media/audio",
    ]

    response = client.get(
        "/api/youtube/download"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data == [
        "D:/media/video",
        "D:/media/audio",
    ]

    mock_get_directories.assert_called_once()


@patch(
    "app.views.api.get_media_directories",
    side_effect=Exception("directory error"),
)
def test_youtube_download_get_error(
    mock_get_directories,
    client,
):
    response = client.get(
        "/api/youtube/download"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert "directory error" in data["error"]


def test_youtube_download_missing_video_id(client):
    response = client.post(
        "/api/youtube/download",
        json={
            "save_dir": "D:/media/video",
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == (
        "video_id and save_dir are required"
    )


def test_youtube_download_missing_save_dir(client):
    response = client.post(
        "/api/youtube/download",
        json={
            "video_id": "abc123",
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == (
        "video_id and save_dir are required"
    )


@patch("app.views.api.download")
def test_youtube_download_success(
    mock_download,
    client,
):
    mock_download.return_value = (
        "D:/media/video/sample.mp4"
    )

    response = client.post(
        "/api/youtube/download",
        json={
            "video_id": "abc123",
            "save_dir": "D:/media/video",
            "save_quality": "720",
            "start_time": "00:01:00",
            "end_time": "00:05:00",
            "download_type": "video",
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["path"] == (
        "D:/media/video/sample.mp4"
    )

    assert "abc123" in data["message"]

    mock_download.assert_called_once_with(
        video_id="abc123",
        save_dir="D:/media/video",
        quality="720",
        start_time="00:01:00",
        end_time="00:05:00",
        download_type="video",
    )


@patch("app.views.api.download")
def test_youtube_download_default_options(
    mock_download,
    client,
):
    mock_download.return_value = "D:/media/video/sample.mp4"

    response = client.post(
        "/api/youtube/download",
        json={
            "video_id": "abc123",
            "save_dir": "D:/media/video",
        },
    )

    assert response.status_code == 200

    mock_download.assert_called_once_with(
        video_id="abc123",
        save_dir="D:/media/video",
        quality="1080",
        start_time=None,
        end_time=None,
        download_type="video",
    )


@patch(
    "app.views.api.download",
    side_effect=Exception("download error"),
)
def test_youtube_download_error(
    mock_download,
    client,
):
    response = client.post(
        "/api/youtube/download",
        json={
            "video_id": "abc123",
            "save_dir": "D:/media/video",
        },
    )

    assert response.status_code == 500

    data = response.get_json()

    assert "download error" in data["error"]

# ==========================================
# 12. YouTube 検索・情報 API
# ==========================================

def test_youtube_search_empty_query(client):
    response = client.get(
        "/api/youtube/search"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["items"] == []


def test_youtube_search_empty_query_explicit(client):
    response = client.get(
        "/api/youtube/search?q="
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["items"] == []


@patch("app.views.api.fetch_youtube_videos")
def test_youtube_search_success(
    mock_fetch,
    client,
):
    mock_fetch.return_value = [
        {
            "id": "abc123",
            "title": "テスト動画",
        },
        {
            "id": "def456",
            "title": "テスト動画2",
        },
    ]

    response = client.get(
        "/api/youtube/search?q=Python"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == "abc123"

    mock_fetch.assert_called_once_with(
        "Python"
    )


@patch(
    "app.views.api.fetch_youtube_videos",
    side_effect=Exception("YouTube API error"),
)
def test_youtube_search_error(
    mock_fetch,
    client,
):
    response = client.get(
        "/api/youtube/search?q=Python"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["error"] == "YouTube API error"


@patch("app.views.api.fetch_youtube_video_info")
def test_youtube_info_success(
    mock_fetch,
    client,
):
    mock_fetch.return_value = {
        "id": "abc123",
        "title": "テスト動画",
        "duration": 120,
    }

    response = client.get(
        "/api/youtube/abc123/info"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == "abc123"
    assert data["title"] == "テスト動画"
    assert data["duration"] == 120

    mock_fetch.assert_called_once_with(
        "abc123"
    )


@patch(
    "app.views.api.fetch_youtube_video_info",
    return_value=None,
)
def test_youtube_info_not_found(
    mock_fetch,
    client,
):
    response = client.get(
        "/api/youtube/nonexistent/info"
    )

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Video not found"


@patch(
    "app.views.api.fetch_youtube_video_info",
    side_effect=Exception("YouTube info error"),
)
def test_youtube_info_error(
    mock_fetch,
    client,
):
    response = client.get(
        "/api/youtube/abc123/info"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["error"] == "YouTube info error"

# ==========================================
# 13. メディアメタデータリセット
# ==========================================

@patch("app.views.api.remove_nonexistent_audio_files_from_db")
@patch("app.views.api.remove_nonexistent_files_from_db")
@patch("app.views.api.rename_musics_and_save_metadata")
@patch("app.views.api.rename_videos_and_save_metadata")
def test_reset_media(
    mock_rename_videos,
    mock_rename_musics,
    mock_remove_videos,
    mock_remove_musics,
    client,
):
    response = client.get(
        "/api/reset/media"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == (
        "メディアメタデータをリセットしました"
    )

    assert mock_rename_videos.call_count == len(MEDIA_BASE_PATHS)
    assert mock_rename_musics.call_count == len(MEDIA_BASE_PATHS)

    mock_remove_videos.assert_called_once()
    mock_remove_musics.assert_called_once()


# ==========================================
# 14. Vocabulary API
# ==========================================

@patch("app.views.api.export_english_vocabulary")
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


@patch("app.views.api.export_single_vocabulary")
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

@patch("app.views.api.copy_code")
def test_copy_code_get(
    mock_copy,
    client,
):
    mock_copy.return_value = [
        "file1.py",
        "file2.py",
    ]

    response = client.get(
        "/api/clipboard/copy-code"
        "?target=test.py"
        "&extension=.py"
        "&extension=.js"
        "&exclude_dir=.git"
        "&recursive=false"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["files"] == [
        "file1.py",
        "file2.py",
    ]
    assert "2 ファイル" in data["message"]

    mock_copy.assert_called_once_with(
        target="test.py",
        extensions=[".py", ".js"],
        exclude_dirs=[".git"],
        recursive=False,
    )

@patch("app.views.api.copy_code")
def test_copy_code_get(
    mock_copy,
    client,
):
    mock_copy.return_value = [
        "file1.py",
        "file2.py",
    ]

    response = client.get(
        "/api/clipboard/copy-code"
        "?target=test.py"
        "&extension=.py"
        "&extension=.js"
        "&exclude_dir=.git"
        "&recursive=false"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["files"] == [
        "file1.py",
        "file2.py",
    ]
    assert "2 ファイル" in data["message"]

    mock_copy.assert_called_once_with(
        target="test.py",
        extensions=[".py", ".js"],
        exclude_dirs=[".git"],
        recursive=False,
    )

# ==========================================
# 16. Markdown / Weather エラー系
# ==========================================

@patch(
    "app.views.api.create_dailynote",
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
    "app.views.api.create_next_weekly_note",
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


@patch(
    "app.views.api.register_today_weather_to_calendar",
    side_effect=Exception("weather error"),
)
def test_register_today_weather_error(
    mock_register,
    client,
):
    response = client.get(
        "/api/weather/get/today"
    )

    # 現在のAPI実装にはtry/exceptがないため、
    # Flaskの500になることを確認する。
    assert response.status_code == 500


@patch(
    "app.views.api.register_tomorrow_weather_to_calendar",
    side_effect=Exception("weather error"),
)
def test_register_tomorrow_weather_error(
    mock_register,
    client,
):
    response = client.get(
        "/api/weather/get/tomorrow"
    )

    # 現在のAPI実装にはtry/exceptがないため、
    # Flaskの500になることを確認する。
    assert response.status_code == 500
