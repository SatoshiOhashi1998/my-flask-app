import os

from app.modules import media_paths


def test_get_video_directories(tmp_path):
    base_path = tmp_path / "video"

    base_path.mkdir()
    (base_path / "movie1").mkdir()
    (base_path / "movie2").mkdir()
    (base_path / "file.txt").touch()

    result = media_paths.get_video_directories(str(base_path))

    assert result == [
        str(base_path / "movie1"),
        str(base_path / "movie2"),
    ]


def test_get_audio_directories(tmp_path):
    base_path = tmp_path / "audio"

    base_path.mkdir()
    (base_path / "music1").mkdir()
    (base_path / "music2").mkdir()

    result = media_paths.get_audio_directories(str(base_path))

    assert result == [
        str(media_paths.AUDIO_BASE_PATH),
        str(base_path / "music1"),
        str(base_path / "music2"),
    ]


def test_get_media_directories(tmp_path, monkeypatch):
    base_path = tmp_path / "media"

    (base_path / "video").mkdir(parents=True)
    (base_path / "video" / "subdir").mkdir()

    monkeypatch.setattr(
        media_paths,
        "MEDIA_BASE_PATHS",
        [str(base_path)],
    )

    result = media_paths.get_media_directories()

    assert str(base_path) in result
    assert str(base_path / "video") in result
    assert str(base_path / "video" / "subdir") in result


def test_get_media_directories_ignores_nonexistent_base_path(
    tmp_path,
    monkeypatch,
):
    valid_path = tmp_path / "valid"
    valid_path.mkdir()

    invalid_path = tmp_path / "not_exists"

    monkeypatch.setattr(
        media_paths,
        "MEDIA_BASE_PATHS",
        [
            str(valid_path),
            str(invalid_path),
        ],
    )

    result = media_paths.get_media_directories()

    assert str(valid_path) in result
    assert str(invalid_path) not in result
