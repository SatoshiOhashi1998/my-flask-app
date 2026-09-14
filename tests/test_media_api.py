from unittest.mock import patch
import locale

from app.models import VideoDataModel, MusicDataModel, db
from app.media.media_paths import MEDIA_BASE_PATHS


# ==========================================
# 動画ストリーミング
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


# ==========================================
# 音声ストリーミング
# ==========================================

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
# Range Request
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
# 動画一覧 / Info
# ==========================================

@patch("app.views.media_api.locale.setlocale")
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


# ==========================================
# 音楽一覧 / Info
# ==========================================

@patch("app.views.media_api.locale.setlocale")
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
# メディアメタデータリセット
# ==========================================

@patch("app.views.media_api.remove_nonexistent_audio_files_from_db")
@patch("app.views.media_api.remove_nonexistent_files_from_db")
@patch("app.views.media_api.rename_musics_and_save_metadata")
@patch("app.views.media_api.rename_videos_and_save_metadata")
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
