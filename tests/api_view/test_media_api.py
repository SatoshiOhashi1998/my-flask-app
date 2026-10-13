from pathlib import Path

import pytest

from app import db
from app.models import MusicDataModel, VideoDataModel


def assert_error(response, status_code, fragment=None):
    assert response.status_code == status_code
    payload = response.get_json()
    assert isinstance(payload.get("error"), str)
    if fragment:
        assert fragment.lower() in payload["error"].lower()


def _create_media(model, *, new_name, path, original_name):
    # The model's string primary key has no default; provide it explicitly.
    item = model(
        id=f"test-{new_name}",
        new_name=new_name,
        path=path,
        original_name=original_name,
    )
    db.session.add(item)
    db.session.commit()
    return item


def test_get_videos_empty(client):
    response = client.get("/api/videos")
    assert response.status_code == 200
    assert isinstance(response.get_json()["data"], list)


def test_get_musics_empty(client):
    response = client.get("/api/musics")
    assert response.status_code == 200
    assert isinstance(response.get_json()["data"], list)


@pytest.mark.parametrize(
    ("endpoint", "model"),
    [
        ("/api/videos", VideoDataModel),
        ("/api/musics", MusicDataModel),
    ],
)
def test_list_media_contains_created_item(client, endpoint, model):
    item = _create_media(
        model,
        new_name="api-test-media",
        path="api-test-media.mp4",
        original_name="original media name",
    )
    response = client.get(endpoint)

    assert response.status_code == 200
    ids = [entry["id"] for entry in response.get_json()["data"]]
    assert item.new_name in ids


def test_get_video_info(client):
    item = _create_media(
        VideoDataModel,
        new_name="video-info",
        path="video-info.mp4",
        original_name="Video Info",
    )
    response = client.get(f"/api/videos/{item.id}/info")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["data"], dict)
    assert payload["data"]["id"] == item.new_name


def test_get_video_info_not_found(client):
    assert_error(client.get("/api/videos/99999999/info"), 404)


def test_get_music_info(client):
    item = _create_media(
        MusicDataModel,
        new_name="music-info",
        path="music-info.mp3",
        original_name="Music Info",
    )
    response = client.get(f"/api/musics/{item.id}/info")

    assert response.status_code == 200
    assert response.get_json()["data"]["id"] == item.new_name


def test_get_music_info_not_found(client):
    assert_error(client.get("/api/musics/99999999/info"), 404)


def test_patch_video_original_name(client):
    item = _create_media(
        VideoDataModel,
        new_name="video-original-name",
        path="123.mp4",
        original_name="before",
    )
    response = client.patch(
        f"/api/videos/{item.id}/original-name",
        json={"original_name": "after"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["original_name"] == "after"
    db.session.refresh(item)
    assert item.original_name == "after"
    # Renaming the display/original name must not rename the physical media path.
    assert item.path == "123.mp4"


def test_patch_music_original_name(client):
    item = _create_media(
        MusicDataModel,
        new_name="music-original-name",
        path="456.mp3",
        original_name="before",
    )
    response = client.patch(
        f"/api/musics/{item.id}/original-name",
        json={"original_name": "after"},
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["original_name"] == "after"
    db.session.refresh(item)
    assert item.path == "456.mp3"


@pytest.mark.parametrize(
    "body",
    [{}, {"original_name": ""}, {"original_name": "   "}, {"original_name": None}],
)
def test_patch_original_name_invalid_body(client, body):
    response = client.patch("/api/videos/1/original-name", json=body)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_patch_video_original_name_not_found(client):
    assert_error(
        client.patch(
            "/api/videos/99999999/original-name",
            json={"original_name": "after"},
        ),
        404,
    )


def test_patch_music_original_name_not_found(client):
    assert_error(
        client.patch(
            "/api/musics/99999999/original-name",
            json={"original_name": "after"},
        ),
        404,
    )


def test_reset_media(client):
    response = client.get("/api/reset/media")
    assert response.status_code == 200
    payload = response.get_json()
    assert "message" in payload
    assert "error" not in payload
