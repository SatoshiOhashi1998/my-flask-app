import pytest

from app.modules import youtube_downloader


def test_extract_youtube_video_id_from_id():
    result = youtube_downloader.extract_youtube_video_id(
        "V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_youtube_url():
    result = youtube_downloader.extract_youtube_video_id(
        "https://www.youtube.com/watch?v=V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_url_with_parameters():
    result = youtube_downloader.extract_youtube_video_id(
        "https://www.youtube.com/watch?v=V0e8h3HiUOo&t=120"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_short_url():
    result = youtube_downloader.extract_youtube_video_id(
        "https://youtu.be/V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_mobile_url():
    result = youtube_downloader.extract_youtube_video_id(
        "https://m.youtube.com/watch?v=V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_strips_whitespace():
    result = youtube_downloader.extract_youtube_video_id(
        "  V0e8h3HiUOo  "
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_rejects_invalid_url():
    with pytest.raises(
        ValueError,
        match="YouTube動画IDを取得できません",
    ):
        youtube_downloader.extract_youtube_video_id(
            "https://example.com/video"
        )


def test_validate_download_params_accepts_time_formats():
    youtube_downloader.validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="1080",
        start_time="01:30",
        end_time="02:30",
        download_type="video",
    )


def test_validate_download_params_accepts_hhmmss():
    youtube_downloader.validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="1080",
        start_time="01:02:30",
        end_time="02:00:00",
        download_type="video",
    )


def test_validate_download_params_accepts_audio_quality_128():
    youtube_downloader.validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="128",
        start_time=None,
        end_time=None,
        download_type="audio",
    )


def test_validate_download_params_accepts_audio_quality_192():
    youtube_downloader.validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="192",
        start_time=None,
        end_time=None,
        download_type="audio",
    )


def test_validate_download_params_accepts_audio_quality_320():
    youtube_downloader.validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="320",
        start_time=None,
        end_time=None,
        download_type="audio",
    )


def test_validate_download_params_accepts_video_download():
    youtube_downloader.validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="1080",
        start_time=None,
        end_time=None,
        download_type="video",
    )


def test_validate_download_params_accepts_audio_download():
    youtube_downloader.validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="192",
        start_time=None,
        end_time=None,
        download_type="audio",
    )


def test_download_builds_video_ydl_options(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "test_video.mp4"
    downloaded_file.write_bytes(b"dummy video")

    captured_options = {}

    class DummyYoutubeDL:
        def __init__(self, options):
            captured_options.update(options)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            assert video_id == "test_video"
            assert download is True

            return {
                "id": video_id,
                "title": "Test Video",
            }

        def prepare_filename(self, info):
            return str(downloaded_file)

    monkeypatch.setattr(
        youtube_downloader.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result, title = youtube_downloader.download_from_youtube(
            "test_video",
            str(tmp_path),
            quality="720",
        )

    assert result == str(downloaded_file)
    assert title == "Test Video"

    assert captured_options["format"] == (
        "bestvideo[height<=720]+bestaudio/best"
    )

    assert captured_options["merge_output_format"] == "mp4"
    assert captured_options["noplaylist"] is True
    assert captured_options["outtmpl"] == (
        str(tmp_path / "%(id)s.%(ext)s")
    )


def test_download_builds_audio_ydl_options(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "test_video.mp3"
    downloaded_file.write_bytes(b"dummy audio")

    captured_options = {}

    class DummyYoutubeDL:
        def __init__(self, options):
            captured_options.update(options)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            assert video_id == "test_video"
            assert download is True

            return {
                "id": video_id,
                "title": "Test Audio",
            }

        def prepare_filename(self, info):
            return str(tmp_path / "test_video.webm")

    monkeypatch.setattr(
        youtube_downloader.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result, title = youtube_downloader.download_from_youtube(
            "test_video",
            str(tmp_path),
            quality="192",
            download_type="audio",
        )

    assert result == str(downloaded_file)
    assert title == "Test Audio"

    assert captured_options["format"] == "bestaudio/best"

    assert captured_options["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ]

    assert captured_options["noplaylist"] is True
    assert captured_options["outtmpl"] == (
        str(tmp_path / "%(id)s.%(ext)s")
    )


def test_download_uses_youtube_cookie_file(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "test_video.mp4"
    downloaded_file.write_bytes(b"dummy video")

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("dummy cookie")

    captured_options = {}

    monkeypatch.setattr(
        youtube_downloader,
        "YOUTUBE_COOKIE_FILE",
        str(cookie_file),
    )

    class DummyYoutubeDL:
        def __init__(self, options):
            captured_options.update(options)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            assert video_id == "test_video"
            assert download is True

            return {
                "id": video_id,
                "title": "Test Video",
            }

        def prepare_filename(self, info):
            return str(downloaded_file)

    monkeypatch.setattr(
        youtube_downloader.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result, title = youtube_downloader.download_from_youtube(
            "test_video",
            str(tmp_path),
        )

    assert result == str(downloaded_file)
    assert title == "Test Video"

    assert captured_options["cookiefile"] == str(cookie_file)


def test_download_ignores_nonexistent_youtube_cookie_file(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "test_video.mp4"
    downloaded_file.write_bytes(b"dummy video")

    cookie_file = tmp_path / "missing_cookies.txt"

    captured_options = {}

    monkeypatch.setattr(
        youtube_downloader,
        "YOUTUBE_COOKIE_FILE",
        str(cookie_file),
    )

    class DummyYoutubeDL:
        def __init__(self, options):
            captured_options.update(options)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            return {
                "id": video_id,
                "title": "Test Video",
            }

        def prepare_filename(self, info):
            return str(downloaded_file)

    monkeypatch.setattr(
        youtube_downloader.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result, title = youtube_downloader.download_from_youtube(
            "test_video",
            str(tmp_path),
        )

    assert result == str(downloaded_file)
    assert title == "Test Video"

    assert "cookiefile" not in captured_options
