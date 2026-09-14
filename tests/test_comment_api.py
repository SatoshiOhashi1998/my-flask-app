from unittest.mock import patch

from app.models import Comment, db


# ==========================================
# コメント取得
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


# ==========================================
# コメント投稿
# ==========================================

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


# ==========================================
# コメント更新
# ==========================================

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


# ==========================================
# コメント削除
# ==========================================

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


# ==========================================
# コメントエクスポート
# ==========================================

@patch("app.views.comment_api.export_today_comments_to_md")
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
# その他コメント
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


# ==========================================
# 存在しないコメント
# ==========================================

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
