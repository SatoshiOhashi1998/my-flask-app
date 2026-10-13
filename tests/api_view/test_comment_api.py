from app import db
from app.models import Comment

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def set_export_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path))

@pytest.fixture(autouse=True)
def setup_summary_environment(tmp_path, monkeypatch):
    export_dir = tmp_path / "exports"
    weekly_dir = tmp_path / "weekly"

    export_dir.mkdir()
    weekly_dir.mkdir()

    monkeypatch.setenv("EXPORT_DIR", str(export_dir))
    monkeypatch.setenv("WEEKLY_NOTE_DIR", str(weekly_dir))

    # サマリー追加先となるウィークリーノートを作成
    weekly_file = weekly_dir / "2026-W42.md"
    weekly_file.write_text(
        "# Weekly Note\n\n"
        "## Comment Summary\n\n"
        "既存の内容\n",
        encoding="utf-8",
    )

def assert_error(response, status_code, fragment=None):
    assert response.status_code == status_code
    payload = response.get_json()
    assert isinstance(payload.get("error"), str)
    if fragment:
        assert fragment.lower() in payload["error"].lower()


def _create_comment(video_id=123, content="original comment", author="tester"):
    comment = Comment(
        video_id=video_id,
        author=author,
        media_type="video",
        content=content,
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def test_get_comments_empty(client):
    response = client.get("/api/comments/987654")
    assert response.status_code == 200
    assert response.get_json()["data"] == []


def test_get_comments(client):
    _create_comment(video_id=123, content="hello")
    response = client.get("/api/comments/123")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["data"], list)
    assert any(item["content"] == "hello" for item in payload["data"])


def test_post_comment(client):
    response = client.post(
        "/api/comments/123",
        json={"content": "new comment", "author": "tester", "media_type": "video"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert "message" in payload
    assert "data" not in payload
    assert Comment.query.filter_by(video_id=123, content="new comment").first() is not None


def test_post_comment_missing_content(client):
    response = client.post("/api/comments/123", json={"author": "tester"})
    assert response.status_code in (400, 422)
    assert "error" in response.get_json()


def test_update_comment(client):
    comment = _create_comment()
    response = client.put(
        f"/api/comments/{comment.id}",
        json={"content": "updated comment"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["content"] == "updated comment"
    db.session.refresh(comment)
    assert comment.content == "updated comment"


def test_update_comment_not_found(client):
    assert_error(
        client.put("/api/comments/99999999", json={"content": "updated"}),
        404,
    )


def test_delete_comment(client):
    comment = _create_comment()
    comment_id = comment.id

    response = client.delete(f"/api/comments/{comment_id}")

    assert response.status_code == 200
    payload = response.get_json()
    assert "message" in payload
    assert "data" not in payload
    assert db.session.get(Comment, comment_id) is None


def test_delete_comment_not_found(client):
    assert_error(client.delete("/api/comments/99999999"), 404)


def test_get_other_comments(client):
    _create_comment(video_id=123, content="target")
    _create_comment(video_id=456, content="other")
    response = client.get("/api/comments/123/others")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["data"], list)
    assert all(item.get("video_id") != 123 for item in payload["data"])


def test_export_comments(client):
    response = client.get("/api/comments/export")
    assert response.status_code == 200
    payload = response.get_json()
    assert "message" in payload
    assert "data" not in payload


def test_export_comments_by_date(client):
    response = client.get("/api/comments/export/2026-10-12")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["date"] == "2026-10-12"
    assert "file_path" in payload["data"]
    assert "message" in payload


def test_export_comments_by_date_invalid(client):
    assert_error(client.get("/api/comments/export/not-a-date"), 400)


def test_add_summary(client):
    response = client.get("/api/comments/add-summary")
    print("status:", response.status_code)
    print("body:", response.get_data(as_text=True))
    assert response.status_code == 200


def test_add_summary_by_date(client):
    response = client.get("/api/comments/add-summary/2026-10-12")
    print("status:", response.status_code)
    print("body:", response.get_data(as_text=True))
    assert response.status_code == 200


def test_add_summary_by_date_invalid(client):
    assert_error(client.get("/api/comments/add-summary/not-a-date"), 400)
