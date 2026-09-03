import os

from app.models import db, VideoDataModel
from app.modules.video_manager import (
    insert_video,
    find_by_id,
    delete_by_id,
    update_video,
    rename_single_video_and_save_metadata,
    rename_videos_and_save_metadata,
    remove_nonexistent_files_from_db,
)


def test_insert_video(client):
    video_id = "test_insert_video"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, video_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_video(
            video_id,
            "original.mp4",
            "new.mp4",
            "/tmp/new.mp4",
        )

        video = db.session.get(VideoDataModel, video_id)

        assert video is not None
        assert video.id == video_id
        assert video.original_name == "original.mp4"
        assert video.new_name == "new.mp4"
        assert video.path == "/tmp/new.mp4"

        db.session.delete(video)
        db.session.commit()


def test_find_by_id(client):
    video_id = "test_find_video"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, video_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_video(
            video_id,
            "original.mp4",
            "new.mp4",
            "/tmp/new.mp4",
        )

        video = find_by_id(video_id)

        assert video is not None
        assert video.id == video_id
        assert video.original_name == "original.mp4"

        assert find_by_id("not_exists_video") is None

        db.session.delete(video)
        db.session.commit()


def test_delete_by_id(client):
    video_id = "test_delete_video"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, video_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_video(
            video_id,
            "original.mp4",
            "new.mp4",
            "/tmp/new.mp4",
        )

        assert find_by_id(video_id) is not None

        result = delete_by_id(video_id)

        assert result is True
        assert find_by_id(video_id) is None

        result = delete_by_id("not_exists_video")

        assert result is False


def test_update_video(client):
    video_id = "test_update_video"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, video_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_video(
            video_id,
            "original.mp4",
            "old.mp4",
            "/tmp/old.mp4",
        )

        result = update_video(
            video_id,
            "new.mp4",
            "/tmp/new.mp4",
        )

        assert result is True

        video = db.session.get(VideoDataModel, video_id)

        assert video is not None
        assert video.new_name == "new.mp4"
        assert video.path == "/tmp/new.mp4"
        assert video.original_name == "original.mp4"

        result = update_video(
            "not_exists_video",
            "new.mp4",
            "/tmp/new.mp4",
        )

        assert result is False

        db.session.delete(video)
        db.session.commit()


def test_rename_single_video_and_save_metadata(
    client,
    tmp_path,
):
    with client.application.app_context():
        video_file = tmp_path / "sample.mp4"
        video_file.write_bytes(b"video data")

        result = rename_single_video_and_save_metadata(
            str(video_file)
        )

        assert result is not None

        new_name, new_path = result

        assert not video_file.exists()
        assert os.path.exists(new_path)
        assert new_name == os.path.basename(new_path)

        video = VideoDataModel.query.filter_by(
            path=new_path
        ).first()

        assert video is not None
        assert video.original_name == "sample.mp4"
        assert video.new_name == new_name
        assert video.path == new_path

        db.session.delete(video)
        db.session.commit()


def test_rename_single_video_ignores_non_video(
    client,
    tmp_path,
):
    with client.application.app_context():
        text_file = tmp_path / "sample.txt"
        text_file.write_text(
            "test",
            encoding="utf-8",
        )

        result = rename_single_video_and_save_metadata(
            str(text_file)
        )

        assert result is None
        assert text_file.exists()

        videos = VideoDataModel.query.filter_by(
            original_name="sample.txt"
        ).all()

        assert videos == []


def test_rename_single_video_ignores_already_renamed_file(
    client,
    tmp_path,
):
    with client.application.app_context():
        video_file = tmp_path / "AbCdEf12345.mp4"
        video_file.write_bytes(b"video data")

        result = rename_single_video_and_save_metadata(
            str(video_file)
        )

        assert result is None
        assert video_file.exists()

        video = VideoDataModel.query.filter_by(
            path=str(video_file)
        ).first()

        assert video is None


def test_rename_videos_and_save_metadata(
    client,
    tmp_path,
):
    with client.application.app_context():
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mkv"
        text_file = tmp_path / "sample.txt"

        video1.write_bytes(b"video 1")
        video2.write_bytes(b"video 2")
        text_file.write_text(
            "text",
            encoding="utf-8",
        )

        result = rename_videos_and_save_metadata(
            str(tmp_path)
        )

        assert len(result) == 2

        assert not video1.exists()
        assert not video2.exists()
        assert text_file.exists()

        videos = VideoDataModel.query.filter(
            VideoDataModel.path.like(f"{tmp_path}%")
        ).all()

        assert len(videos) == 2

        for video in videos:
            assert os.path.exists(video.path)

            db.session.delete(video)

        db.session.commit()


def test_remove_nonexistent_files_from_db(
    client,
    tmp_path,
):
    video_id = "test_remove_nonexistent"

    with client.application.app_context():
        existing = db.session.get(VideoDataModel, video_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        nonexistent_path = (
            tmp_path / "does_not_exist.mp4"
        )

        insert_video(
            video_id,
            "missing.mp4",
            "missing.mp4",
            str(nonexistent_path),
        )

        assert (
            db.session.get(VideoDataModel, video_id)
            is not None
        )

        removed = remove_nonexistent_files_from_db()

        assert str(nonexistent_path) in removed
        assert (
            db.session.get(VideoDataModel, video_id)
            is None
        )
