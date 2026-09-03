from app.models import db, VideoDataModel, MusicDataModel

from app.modules.media_manager import (
    insert_media,
    find_by_id,
    delete_by_id,
    remove_nonexistent_files,
)


def test_insert_media(client):
    media_id = "test_media_insert"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, media_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_media(
            VideoDataModel,
            media_id,
            "original.mp4",
            "new.mp4",
            "/tmp/new.mp4",
        )

        video = db.session.get(
            VideoDataModel,
            media_id,
        )

        assert video is not None
        assert video.id == media_id
        assert video.original_name == "original.mp4"
        assert video.new_name == "new.mp4"
        assert video.path == "/tmp/new.mp4"

        db.session.delete(video)
        db.session.commit()


def test_find_by_id(client):
    media_id = "test_media_find"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, media_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_media(
            VideoDataModel,
            media_id,
            "original.mp4",
            "new.mp4",
            "/tmp/new.mp4",
        )

        video = find_by_id(
            VideoDataModel,
            media_id,
        )

        assert video is not None
        assert video.id == media_id
        assert video.original_name == "original.mp4"

        assert (
            find_by_id(
                VideoDataModel,
                "not_exists_media",
            )
            is None
        )

        db.session.delete(video)
        db.session.commit()


def test_delete_by_id(client):
    media_id = "test_media_delete"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, media_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_media(
            VideoDataModel,
            media_id,
            "original.mp4",
            "new.mp4",
            "/tmp/new.mp4",
        )

        assert (
            find_by_id(
                VideoDataModel,
                media_id,
            )
            is not None
        )

        result = delete_by_id(
            VideoDataModel,
            media_id,
        )

        assert result is True

        assert (
            find_by_id(
                VideoDataModel,
                media_id,
            )
            is None
        )

        result = delete_by_id(
            VideoDataModel,
            "not_exists_media",
        )

        assert result is False


def test_remove_nonexistent_files(client, tmp_path):
    media_id = "test_media_remove"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, media_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        nonexistent_path = (
            tmp_path / "does_not_exist.mp4"
        )

        insert_media(
            VideoDataModel,
            media_id,
            "missing.mp4",
            "missing.mp4",
            str(nonexistent_path),
        )

        assert (
            db.session.get(
                VideoDataModel,
                media_id,
            )
            is not None
        )

        removed = remove_nonexistent_files(
            VideoDataModel
        )

        assert str(nonexistent_path) in removed

        assert (
            db.session.get(
                VideoDataModel,
                media_id,
            )
            is None
        )


def test_media_manager_works_with_music(client):
    media_id = "test_media_music"

    with client.application.app_context():
        existing = db.session.get(MusicDataModel, media_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_media(
            MusicDataModel,
            media_id,
            "original.mp3",
            "new.mp3",
            "/tmp/new.mp3",
        )

        music = find_by_id(
            MusicDataModel,
            media_id,
        )

        assert music is not None
        assert music.id == media_id
        assert music.original_name == "original.mp3"
        assert music.new_name == "new.mp3"
        assert music.path == "/tmp/new.mp3"

        result = delete_by_id(
            MusicDataModel,
            media_id,
        )

        assert result is True

        assert (
            find_by_id(
                MusicDataModel,
                media_id,
            )
            is None
        )
    