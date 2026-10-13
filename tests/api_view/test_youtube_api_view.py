from unittest.mock import patch

import pytest


def assert_error(response, status_code, fragment=None):
    assert response.status_code == status_code
    payload = response.get_json()
    assert isinstance(payload.get("error"), str)
    if fragment:
        assert fragment.lower() in payload["error"].lower()


def test_youtube_download_get_success(client):
    with patch(
        "app.views.youtube_api_view.get_media_directories",
        return_value=["D:/media/videos", "D:/media/music"],
    ):
        response = client.get("/api/youtube/download")

    assert response.status_code == 200
    assert response.get_json()["data"] == ["D:/media/videos", "D:/media/music"]


def test_youtube_download_get_error(client):
    with patch(
        "app.views.youtube_api_view.get_media_directories",
        side_effect=RuntimeError("directory lookup failed"),
    ):
        response = client.get("/api/youtube/download")

    assert_error(response, 500)


def test_youtube_download_missing_video_id(client):
    response = client.post(
        "/api/youtube/download",
        json={"save_dir": "D:/media"},
    )
    assert_error(response, 400)


def test_youtube_download_missing_save_dir(client):
    response = client.post(
        "/api/youtube/download",
        json={"video_id": "abc123"},
    )
    assert_error(response, 400)


def test_youtube_download_success(client):
    with patch(
        "app.views.youtube_api_view.download",
        return_value="D:/media/abc123.mp4",
    ) as download:
        response = client.post(
            "/api/youtube/download",
            json={"video_id": "abc123", "save_dir": "D:/media"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["path"] == "D:/media/abc123.mp4"
    assert "message" in payload
    download.assert_called_once()


def test_youtube_download_error(client):
    with patch(
        "app.views.youtube_api_view.download",
        side_effect=RuntimeError("download failed"),
    ):
        response = client.post(
            "/api/youtube/download",
            json={"video_id": "abc123", "save_dir": "D:/media"},
        )

    assert_error(response, 500)


def test_youtube_search_empty_query(client):
    response = client.get("/api/youtube/search")
    assert response.status_code == 200
    assert response.get_json()["data"] == []


def test_youtube_search_empty_query_explicit(client):
    response = client.get("/api/youtube/search?q=")
    assert response.status_code == 200
    assert response.get_json()["data"] == []


def test_youtube_search_success(client):
    expected = [
        {"id": "abc123", "filetitle": "First video", "type": "youtube"},
        {"id": "def456", "filetitle": "Second video", "type": "youtube"},
    ]
    with patch(
        "app.views.youtube_api_view.fetch_youtube_videos",
        return_value=expected,
    ) as fetch:
        response = client.get("/api/youtube/search?q=test")

    assert response.status_code == 200
    items = response.get_json()["data"]
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0]["id"] == "abc123"
    fetch.assert_called_once_with("test")


def test_youtube_search_error(client):
    with patch(
        "app.views.youtube_api_view.fetch_youtube_videos",
        side_effect=RuntimeError("search failed"),
    ):
        response = client.get("/api/youtube/search?q=test")

    assert_error(response, 500)


def test_youtube_info_success(client):
    expected = {"id": "abc123", "title": "Example video"}
    with patch(
        "app.views.youtube_api_view.fetch_youtube_video_info",
        return_value=expected,
    ):
        response = client.get("/api/youtube/abc123/info")

    assert response.status_code == 200
    assert response.get_json()["data"] == expected


def test_youtube_info_not_found(client):
    with patch(
        "app.views.youtube_api_view.fetch_youtube_video_info",
        return_value=None,
    ):
        response = client.get("/api/youtube/nonexistent/info")

    assert_error(response, 404)


def test_youtube_info_error(client):
    with patch(
        "app.views.youtube_api_view.fetch_youtube_video_info",
        side_effect=RuntimeError("YouTube info error"),
    ):
        response = client.get("/api/youtube/abc123/info")

    assert_error(response, 500)
