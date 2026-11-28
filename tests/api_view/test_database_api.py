from app.models import Comment, Vocabulary, VideoDataModel, db


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
