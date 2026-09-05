import os

from app.models import db, MusicDataModel
from app.modules.audio_manager import (
    insert_music,
    find_by_id,
    delete_by_id,
    rename_single_music_and_save_metadata,
    rename_musics_and_save_metadata,
    remove_nonexistent_audio_files_from_db,
)


def test_insert_music(client):
    music_id = "test_insert_music"

    with client.application.app_context():
        existing = db.session.get(MusicDataModel, music_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_music(
            music_id,
            "original.mp3",
            "new.mp3",
            "/tmp/new.mp3",
        )

        music = db.session.get(MusicDataModel, music_id)

        assert music is not None
        assert music.id == music_id
        assert music.original_name == "original.mp3"
        assert music.new_name == "new.mp3"
        assert music.path == "/tmp/new.mp3"

        db.session.delete(music)
        db.session.commit()


def test_find_by_id(client):
    music_id = "test_find_music"

    with client.application.app_context():
        existing = db.session.get(MusicDataModel, music_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_music(
            music_id,
            "original.mp3",
            "new.mp3",
            "/tmp/new.mp3",
        )

        music = find_by_id(music_id)

        assert music is not None
        assert music.id == music_id
        assert music.original_name == "original.mp3"

        assert find_by_id("not_exists_music") is None

        db.session.delete(music)
        db.session.commit()


def test_delete_by_id(client):
    music_id = "test_delete_music"

    with client.application.app_context():
        existing = db.session.get(MusicDataModel, music_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        insert_music(
            music_id,
            "original.mp3",
            "new.mp3",
            "/tmp/new.mp3",
        )

        assert find_by_id(music_id) is not None

        result = delete_by_id(music_id)

        assert result is True
        assert find_by_id(music_id) is None

        result = delete_by_id("not_exists_music")

        assert result is False


def test_rename_single_music_and_save_metadata(
    client,
    tmp_path,
):
    with client.application.app_context():
        music_file = tmp_path / "sample.mp3"
        music_file.write_bytes(b"music data")

        result = rename_single_music_and_save_metadata(
            str(music_file)
        )

        assert result is not None

        new_name, new_path = result

        assert not music_file.exists()
        assert os.path.exists(new_path)
        assert new_name == os.path.basename(new_path)

        music = MusicDataModel.query.filter_by(
            path=new_path
        ).first()

        assert music is not None
        assert music.original_name == "sample.mp3"
        assert music.new_name == new_name
        assert music.path == new_path

        db.session.delete(music)
        db.session.commit()


def test_rename_single_music_ignores_non_music(
    client,
    tmp_path,
):
    with client.application.app_context():
        text_file = tmp_path / "sample.txt"
        text_file.write_text(
            "test",
            encoding="utf-8",
        )

        result = rename_single_music_and_save_metadata(
            str(text_file)
        )

        assert result is None
        assert text_file.exists()

        musics = MusicDataModel.query.filter_by(
            original_name="sample.txt"
        ).all()

        assert musics == []


def test_rename_single_music_ignores_already_renamed_file(
    client,
    tmp_path,
):
    with client.application.app_context():
        music_file = tmp_path / "AbCdEf12345.mp3"
        music_file.write_bytes(b"music data")

        result = rename_single_music_and_save_metadata(
            str(music_file)
        )

        assert result is None
        assert music_file.exists()

        music = MusicDataModel.query.filter_by(
            path=str(music_file)
        ).first()

        assert music is None


def test_rename_musics_and_save_metadata(
    client,
    tmp_path,
):
    with client.application.app_context():
        music1 = tmp_path / "music1.mp3"
        music2 = tmp_path / "music2.wav"
        text_file = tmp_path / "sample.txt"

        music1.write_bytes(b"music 1")
        music2.write_bytes(b"music 2")
        text_file.write_text(
            "text",
            encoding="utf-8",
        )

        result = rename_musics_and_save_metadata(
            str(tmp_path)
        )

        assert len(result) == 2

        assert not music1.exists()
        assert not music2.exists()
        assert text_file.exists()

        musics = MusicDataModel.query.filter(
            MusicDataModel.path.like(f"{tmp_path}%")
        ).all()

        assert len(musics) == 2

        for music in musics:
            assert os.path.exists(music.path)

            db.session.delete(music)

        db.session.commit()


def test_remove_nonexistent_audio_files_from_db(
    client,
    tmp_path,
):
    music_id = "test_remove_nonexistent"

    with client.application.app_context():
        existing = db.session.get(MusicDataModel, music_id)

        if existing:
            db.session.delete(existing)
            db.session.commit()

        nonexistent_path = (
            tmp_path / "does_not_exist.mp3"
        )

        insert_music(
            music_id,
            "missing.mp3",
            "missing.mp3",
            str(nonexistent_path),
        )

        assert (
            db.session.get(MusicDataModel, music_id)
            is not None
        )

        removed = remove_nonexistent_audio_files_from_db()

        assert str(nonexistent_path) in removed
        assert (
            db.session.get(MusicDataModel, music_id)
            is None
        )
