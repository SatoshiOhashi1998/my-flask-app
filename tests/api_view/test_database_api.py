from app.models import Comment, MusicDataModel, Vocabulary, VideoDataModel, db


def test_database_resource_list_and_create_video(client):
    response = client.post(
        "/api/database/videos",
        json={
            "id": "video-001",
            "new_name": "video-001.mp4",
            "path": "/media/video-001.mp4",
            "original_name": "テスト動画",
        },
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["id"] == "video-001"

    response = client.get("/api/database/videos")
    assert response.status_code == 200
    assert response.get_json()["data"][0]["original_name"] == "テスト動画"


def test_database_resource_rejects_unknown_fields(client):
    response = client.post(
        "/api/database/videos",
        json={
            "id": "video-002",
            "new_name": "video-002.mp4",
            "path": "/media/video-002.mp4",
            "original_name": "テスト",
            "unexpected": True,
        },
    )
    assert response.status_code == 400


def test_database_resource_patch_and_delete_comment(client):
    comment = Comment(
        video_id="video-123",
        author="tester",
        media_type="youtube",
        content="before",
    )
    db.session.add(comment)
    db.session.commit()

    response = client.patch(
        f"/api/database/comments/{comment.id}",
        json={"content": "after"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["content"] == "after"

    response = client.delete(f"/api/database/comments/{comment.id}")
    assert response.status_code == 200
    assert db.session.get(Comment, comment.id) is None


def test_database_resource_create_and_get_vocabulary(client):
    response = client.post(
        "/api/database/vocabularies",
        json={"word": "cache", "meaning": "データを一時保存する仕組み"},
    )
    assert response.status_code == 201
    vocabulary_id = response.get_json()["data"]["id"]

    response = client.get(f"/api/database/vocabularies/{vocabulary_id}")
    assert response.status_code == 200
    assert response.get_json()["data"]["word"] == "cache"


def test_database_resource_not_found(client):
    response = client.get("/api/database/unknown-resource")
    assert response.status_code == 404

    response = client.get("/api/database/comments/999999")
    assert response.status_code == 404



def test_database_video_uses_media_id_for_read_update_and_delete(client):
    video = VideoDataModel(
        id="internal-video-primary-key",
        new_name="public-video-id.mp4",
        path="/media/public-video-id.mp4",
        original_name="テスト動画",
    )
    db.session.add(video)
    db.session.commit()

    response = client.get("/api/database/videos")
    assert response.status_code == 200
    assert any(
        item["id"] == "public-video-id"
        for item in response.get_json()["data"]
    )

    response = client.get("/api/database/videos/public-video-id")
    assert response.status_code == 200
    assert response.get_json()["data"]["id"] == "public-video-id"

    response = client.patch(
        "/api/database/videos/public-video-id",
        json={"original_name": "更新後の動画"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["original_name"] == "更新後の動画"

    response = client.delete("/api/database/videos/public-video-id")
    assert response.status_code == 200
    assert db.session.get(VideoDataModel, "internal-video-primary-key") is None


def test_database_music_uses_media_id_for_read_update_and_delete(client):
    music = MusicDataModel(
        id="internal-music-primary-key",
        new_name="public-music-id.mp3",
        path="/media/public-music-id.mp3",
        original_name="テスト音楽",
    )
    db.session.add(music)
    db.session.commit()

    response = client.get("/api/database/musics/public-music-id")
    assert response.status_code == 200
    assert response.get_json()["data"]["id"] == "public-music-id"

    response = client.patch(
        "/api/database/musics/public-music-id",
        json={"original_name": "更新後の音楽"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["original_name"] == "更新後の音楽"

    response = client.delete("/api/database/musics/public-music-id")
    assert response.status_code == 200
    assert db.session.get(MusicDataModel, "internal-music-primary-key") is None
