from unittest.mock import patch


# ==========================================
# YouTube ダウンロード API
# ==========================================

@patch("app.views.youtube_api_view.get_media_directories")
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
    "app.views.youtube_api_view.get_media_directories",
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


@patch("app.views.youtube_api_view.download")
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


@patch("app.views.youtube_api_view.download")
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
    "app.views.youtube_api_view.download",
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
# YouTube 検索 API
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


@patch("app.views.youtube_api_view.fetch_youtube_videos")
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
    "app.views.youtube_api_view.fetch_youtube_videos",
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


# ==========================================
# YouTube 情報 API
# ==========================================

@patch("app.views.youtube_api_view.fetch_youtube_video_info")
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
    "app.views.youtube_api_view.fetch_youtube_video_info",
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
    "app.views.youtube_api_view.fetch_youtube_video_info",
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
