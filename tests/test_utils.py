import os
import pytest

from app.models import db, VideoDataModel, MusicDataModel
from app import utils


def test_download_registers_video_to_db(client, tmp_path, monkeypatch):
    video_id = "test_download_video"
    downloaded_file = tmp_path / "downloaded.mp4"

    # ダウンロード済みファイルを作成
    downloaded_file.write_bytes(b"dummy video")

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

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
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        # 前回のテストデータを削除
        existing = db.session.get(
            VideoDataModel,
            video_id,
        )

        if existing:
            db.session.delete(existing)
            db.session.commit()

        result = utils.download(
            video_id,
            str(tmp_path),
            quality="1080",
            download_type="video",
        )

        # 戻り値
        assert result == str(downloaded_file.resolve())

        # DB登録を確認
        video = db.session.get(
            VideoDataModel,
            video_id,
        )

        assert video is not None
        assert video.id == video_id
        assert video.original_name == "Test Video"
        assert video.new_name == "downloaded.mp4"
        assert video.path == str(downloaded_file.resolve())

        # 後始末
        db.session.delete(video)
        db.session.commit()


def test_download_registers_audio_to_db(client, tmp_path, monkeypatch):
    music_id = "test_download_audio"

    downloaded_mp3 = tmp_path / "downloaded.mp3"

    # ダウンロード済みmp3を作成
    downloaded_mp3.write_bytes(b"dummy audio")

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            return {
                "id": video_id,
                "title": "Test Audio",
            }

        def prepare_filename(self, info):
            # download() 内で .mp3 に変更されることを考慮
            return str(tmp_path / "downloaded.webm")

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        # 前回のテストデータを削除
        existing = db.session.get(
            MusicDataModel,
            music_id,
        )

        if existing:
            db.session.delete(existing)
            db.session.commit()

        result = utils.download(
            music_id,
            str(tmp_path),
            quality="192",
            download_type="audio",
        )

        # 戻り値
        assert result == str(downloaded_mp3.resolve())

        # DB登録を確認
        music = db.session.get(
            MusicDataModel,
            music_id,
        )

        assert music is not None
        assert music.id == music_id
        assert music.original_name == "Test Audio"
        assert music.new_name == "downloaded.mp3"
        assert music.path == str(downloaded_mp3.resolve())

        # 後始末
        db.session.delete(music)
        db.session.commit()


def test_download_removes_nonexistent_video_records(
    client,
    tmp_path,
    monkeypatch,
):
    video_id = "test_download_cleanup"

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            return {
                "id": video_id,
                "title": "Cleanup Test",
            }

        def prepare_filename(self, info):
            return str(tmp_path / "downloaded.mp4")

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        # 存在しないファイルを指すDBレコードを作成
        nonexistent = tmp_path / "does_not_exist.mp4"

        existing = db.session.get(
            VideoDataModel,
            "old_video",
        )

        if existing:
            db.session.delete(existing)
            db.session.commit()

        old_video = VideoDataModel(
            id="old_video",
            original_name="Old Video",
            new_name="old.mp4",
            path=str(nonexistent),
        )

        db.session.add(old_video)
        db.session.commit()

        # 新しくダウンロードされるファイル
        downloaded_file = tmp_path / "downloaded.mp4"
        downloaded_file.write_bytes(b"dummy video")

        result = utils.download(
            video_id,
            str(tmp_path),
            download_type="video",
        )

        assert result == str(downloaded_file.resolve())

        # 存在しないファイルのDBレコードが削除されている
        assert (
            db.session.get(
                VideoDataModel,
                "old_video",
            )
            is None
        )

        # 新しい動画は登録されている
        video = db.session.get(
            VideoDataModel,
            video_id,
        )

        assert video is not None

        # 後始末
        db.session.delete(video)
        db.session.commit()


def test_download_db_error_does_not_raise(
    client,
    tmp_path,
    monkeypatch,
):
    video_id = "test_download_db_error"

    downloaded_file = tmp_path / "downloaded.mp4"
    downloaded_file.write_bytes(b"dummy video")

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            return {
                "id": video_id,
                "title": "DB Error Test",
            }

        def prepare_filename(self, info):
            return str(downloaded_file)

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    def raise_db_error(*args, **kwargs):
        raise Exception("DB error")

    monkeypatch.setattr(
        utils,
        "insert_media",
        raise_db_error,
    )

    with client.application.app_context():
        result = utils.download(
            video_id,
            str(tmp_path),
            download_type="video",
        )

        # 現在の仕様ではDBエラーを握りつぶし、
        # ダウンロード自体は成功として扱う
        assert result == str(downloaded_file.resolve())

        video = db.session.get(
            VideoDataModel,
            video_id,
        )

        assert video is None

def test_download_rejects_empty_video_id():
    with pytest.raises(ValueError, match="video_idは空にできません"):
        utils.download(
            "   ",
            "dummy_dir",
        )


def test_download_rejects_invalid_download_type():
    with pytest.raises(ValueError, match="download_typeが不正です"):
        utils.download(
            "test_video",
            "dummy_dir",
            download_type="invalid",
        )


def test_download_rejects_invalid_audio_quality():
    with pytest.raises(ValueError, match="音声のqualityが不正です"):
        utils.download(
            "test_video",
            "dummy_dir",
            quality="256",
            download_type="audio",
        )


def test_download_rejects_invalid_video_quality():
    with pytest.raises(ValueError, match="動画のqualityが不正です"):
        utils.download(
            "test_video",
            "dummy_dir",
            quality="abc",
            download_type="video",
        )


def test_download_rejects_negative_video_quality():
    with pytest.raises(ValueError, match="正の整数"):
        utils.download(
            "test_video",
            "dummy_dir",
            quality="-1",
            download_type="video",
        )


def test_download_rejects_invalid_start_time():
    with pytest.raises(ValueError, match="時間指定の形式が不正です"):
        utils.download(
            "test_video",
            "dummy_dir",
            start_time="abc",
        )


def test_download_rejects_invalid_end_time():
    with pytest.raises(ValueError, match="時間指定の形式が不正です"):
        utils.download(
            "test_video",
            "dummy_dir",
            end_time="abc",
        )


def test_download_rejects_invalid_time_range():
    with pytest.raises(ValueError, match="start_timeはend_timeより前"):
        utils.download(
            "test_video",
            "dummy_dir",
            start_time="02:00",
            end_time="01:00",
        )

def test_download_with_trim_overwrite(
    client,
    tmp_path,
    monkeypatch,
):
    video_id = "test_trim_overwrite"

    downloaded_file = tmp_path / "downloaded.mp4"
    downloaded_file.write_bytes(b"original video")

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            return {
                "id": video_id,
                "title": "Trim Overwrite Test",
            }

        def prepare_filename(self, info):
            return str(downloaded_file)

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    def fake_input(*args, **kwargs):
        return object()

    def fake_output(stream, output_file, **kwargs):
        return output_file

    def fake_run(stream, overwrite_output, cmd):
        with open(stream, "wb") as f:
            f.write(b"trimmed video")

    monkeypatch.setattr(
        utils.ffmpeg,
        "input",
        fake_input,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "output",
        fake_output,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "run",
        fake_run,
    )

    with client.application.app_context():
        result = utils.download(
            video_id,
            str(tmp_path),
            start_time="00:10",
            end_time="00:20",
            trim_overwrite=True,
            download_type="video",
        )

        assert result == str(downloaded_file.resolve())

        # トリミング後の内容で上書きされている
        assert downloaded_file.read_bytes() == b"trimmed video"

        # DB登録も確認
        video = db.session.get(
            VideoDataModel,
            video_id,
        )

        assert video is not None
        assert video.path == str(downloaded_file.resolve())

        # 後始末
        db.session.delete(video)
        db.session.commit()

def test_download_with_trim_without_overwrite(
    client,
    tmp_path,
    monkeypatch,
):
    video_id = "test_trim_no_overwrite"

    downloaded_file = tmp_path / "downloaded.mp4"
    downloaded_file.write_bytes(b"original video")

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            return {
                "id": video_id,
                "title": "Trim No Overwrite Test",
            }

        def prepare_filename(self, info):
            return str(downloaded_file)

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    def fake_input(*args, **kwargs):
        return object()

    def fake_output(stream, output_file, **kwargs):
        return output_file

    def fake_run(stream, overwrite_output, cmd):
        with open(stream, "wb") as f:
            f.write(b"trimmed video")

    monkeypatch.setattr(
        utils.ffmpeg,
        "input",
        fake_input,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "output",
        fake_output,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "run",
        fake_run,
    )

    with client.application.app_context():
        result = utils.download(
            video_id,
            str(tmp_path),
            start_time="00:10",
            end_time="00:20",
            trim_overwrite=False,
            download_type="video",
        )

        trimmed_file = tmp_path / "downloaded.tmp.mp4"

        # 戻り値はトリミング後の別ファイル
        assert result == str(trimmed_file.resolve())

        # 元ファイルはそのまま残っている
        assert downloaded_file.read_bytes() == b"original video"

        # トリミング後のファイルが存在する
        assert trimmed_file.exists()
        assert trimmed_file.read_bytes() == b"trimmed video"

        # DBにはトリミング後のファイルが登録される
        video = db.session.get(
            VideoDataModel,
            video_id,
        )

        assert video is not None
        assert video.path == str(trimmed_file.resolve())
        assert video.new_name == "downloaded.tmp.mp4"

        # 後始末
        db.session.delete(video)
        db.session.commit()


def test_extract_youtube_video_id_from_id():
    result = utils._extract_youtube_video_id(
        "V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_youtube_url():
    result = utils._extract_youtube_video_id(
        "https://www.youtube.com/watch?v=V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_url_with_parameters():
    result = utils._extract_youtube_video_id(
        "https://www.youtube.com/watch?v=V0e8h3HiUOo&t=120"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_short_url():
    result = utils._extract_youtube_video_id(
        "https://youtu.be/V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_from_mobile_url():
    result = utils._extract_youtube_video_id(
        "https://m.youtube.com/watch?v=V0e8h3HiUOo"
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_strips_whitespace():
    result = utils._extract_youtube_video_id(
        "  V0e8h3HiUOo  "
    )

    assert result == "V0e8h3HiUOo"


def test_extract_youtube_video_id_rejects_invalid_url():
    with pytest.raises(
        ValueError,
        match="YouTube動画IDを取得できません",
    ):
        utils._extract_youtube_video_id(
            "https://example.com/video"
        )

def test_download_rejects_empty_save_dir():
    with pytest.raises(
        ValueError,
        match="save_dirは空にできません",
    ):
        utils.download(
            "test_video",
            "",
        )

def test_download_rejects_save_dir_that_is_file(tmp_path):
    file_path = tmp_path / "not_directory.txt"
    file_path.write_text("dummy")

    with pytest.raises(
        ValueError,
        match="save_dirがディレクトリではありません",
    ):
        utils.download(
            "test_video",
            str(file_path),
        )

def test_validate_download_params_accepts_time_formats():
    utils._validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="1080",
        start_time="01:30",
        end_time="02:30",
        download_type="video",
    )


def test_validate_download_params_accepts_hhmmss():
    utils._validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="1080",
        start_time="01:02:30",
        end_time="02:00:00",
        download_type="video",
    )

def test_download_accepts_youtube_url(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "downloaded.mp4"
    downloaded_file.write_bytes(b"dummy video")

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            # URLではなく、動画IDに変換されていることを確認
            assert video_id == "test_video"
            assert download is True

            return {
                "id": video_id,
                "title": "Test Video",
            }

        def prepare_filename(self, info):
            return str(downloaded_file)

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result = utils.download(
            "https://www.youtube.com/watch?v=test_video&t=30",
            str(tmp_path),
        )

        assert result == str(downloaded_file.resolve())

        video = db.session.get(
            VideoDataModel,
            "test_video",
        )

        assert video is not None

        db.session.delete(video)
        db.session.commit()

def test_validate_download_params_accepts_audio_quality_128():
    utils._validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="128",
        start_time=None,
        end_time=None,
        download_type="audio",
    )


def test_validate_download_params_accepts_audio_quality_192():
    utils._validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="192",
        start_time=None,
        end_time=None,
        download_type="audio",
    )


def test_validate_download_params_accepts_audio_quality_320():
    utils._validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="320",
        start_time=None,
        end_time=None,
        download_type="audio",
    )

def test_validate_download_params_accepts_video_download():
    utils._validate_download_params(
        video_id="test_video",
        save_dir="dummy_dir",
        quality="1080",
        start_time=None,
        end_time=None,
        download_type="video",
    )


def test_validate_download_params_accepts_audio_download():
    utils._validate_download_params(
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
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result = utils.download(
            "test_video",
            str(tmp_path),
            quality="720",
        )

    assert result == str(downloaded_file.resolve())

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
            # yt-dlpのprepare_filename()は変換前の拡張子を返す想定
            return str(tmp_path / "test_video.webm")

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result = utils.download(
            "test_video",
            str(tmp_path),
            quality="192",
            download_type="audio",
        )

    assert result == str(downloaded_file.resolve())

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
        utils,
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
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result = utils.download(
            "test_video",
            str(tmp_path),
        )

    assert result == str(downloaded_file.resolve())

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
        utils,
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
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    with client.application.app_context():
        result = utils.download(
            "test_video",
            str(tmp_path),
        )

    assert result == str(downloaded_file.resolve())

    assert "cookiefile" not in captured_options

def test_download_video_trim_uses_correct_ffmpeg_options(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "test_video.mp4"
    downloaded_file.write_bytes(b"dummy video")

    output_file = tmp_path / "test_video.tmp.mp4"

    captured_input = {}
    captured_output = {}
    captured_run = {}

    class DummyYoutubeDL:
        def __init__(self, options):
            pass

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

    def dummy_input(filename, ss=None, to=None):
        captured_input["filename"] = filename
        captured_input["ss"] = ss
        captured_input["to"] = to
        return "input_stream"

    def dummy_output(stream, filename, vcodec=None, acodec=None):
        captured_output["stream"] = stream
        captured_output["filename"] = filename
        captured_output["vcodec"] = vcodec
        captured_output["acodec"] = acodec
        return "output_stream"

    def dummy_run(
        stream,
        overwrite_output=False,
        cmd=None,
    ):
        captured_run["stream"] = stream
        captured_run["overwrite_output"] = overwrite_output
        captured_run["cmd"] = cmd

        # ffmpegが生成したファイルを再現
        output_file.write_bytes(b"trimmed video")

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "input",
        dummy_input,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "output",
        dummy_output,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "run",
        dummy_run,
    )

    with client.application.app_context():
        result = utils.download(
            "test_video",
            str(tmp_path),
            start_time="01:00",
            end_time="02:00",
        )

    assert result == str(downloaded_file.resolve())

    assert captured_input == {
        "filename": str(downloaded_file),
        "ss": "01:00",
        "to": "02:00",
    }

    assert captured_output == {
        "stream": "input_stream",
        "filename": str(output_file),
        "vcodec": "libx264",
        "acodec": "aac",
    }

    assert captured_run["stream"] == "output_stream"
    assert captured_run["overwrite_output"] is True

def test_download_audio_trim_uses_correct_ffmpeg_options(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "test_audio.mp3"
    downloaded_file.write_bytes(b"dummy audio")

    output_file = tmp_path / "test_audio.tmp.mp3"

    captured_input = {}
    captured_output = {}

    class DummyYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, video_id, download=True):
            return {
                "id": video_id,
                "title": "Test Audio",
            }

        def prepare_filename(self, info):
            return str(tmp_path / "test_audio.webm")

    def dummy_input(filename, ss=None, to=None):
        captured_input["filename"] = filename
        captured_input["ss"] = ss
        captured_input["to"] = to
        return "input_stream"

    def dummy_output(stream, filename, acodec=None):
        captured_output["stream"] = stream
        captured_output["filename"] = filename
        captured_output["acodec"] = acodec
        return "output_stream"

    def dummy_run(
        stream,
        overwrite_output=False,
        cmd=None,
    ):
        output_file.write_bytes(b"trimmed audio")

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "input",
        dummy_input,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "output",
        dummy_output,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "run",
        dummy_run,
    )

    # download() は .webm → .mp3 と変換した
    # ファイルを探すため、実際のmp3を用意する
    downloaded_file.write_bytes(b"dummy audio")

    with client.application.app_context():
        result = utils.download(
            "test_audio",
            str(tmp_path),
            quality="192",
            start_time="01:00",
            end_time="02:00",
            download_type="audio",
        )

    assert result == str(downloaded_file.resolve())

    assert captured_input == {
        "filename": str(downloaded_file),
        "ss": "01:00",
        "to": "02:00",
    }

    assert captured_output == {
        "stream": "input_stream",
        "filename": str(output_file),
        "acodec": "libmp3lame",
    }

def test_download_trim_error_removes_output_file(
    client,
    tmp_path,
    monkeypatch,
):
    downloaded_file = tmp_path / "test_video.mp4"
    downloaded_file.write_bytes(b"dummy video")

    output_file = tmp_path / "test_video.tmp.mp4"

    class DummyYoutubeDL:
        def __init__(self, options):
            pass

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

    def dummy_input(filename, ss=None, to=None):
        return "input_stream"

    def dummy_output(stream, filename, vcodec=None, acodec=None):
        # FFmpegが出力ファイルを作った状態を再現
        output_file.write_bytes(b"partial output")
        return "output_stream"

    def dummy_run(
        stream,
        overwrite_output=False,
        cmd=None,
    ):
        raise RuntimeError("FFmpeg failed")

    monkeypatch.setattr(
        utils.yt_dlp,
        "YoutubeDL",
        DummyYoutubeDL,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "input",
        dummy_input,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "output",
        dummy_output,
    )

    monkeypatch.setattr(
        utils.ffmpeg,
        "run",
        dummy_run,
    )

    with client.application.app_context():
        with pytest.raises(
            RuntimeError,
            match="トリミング処理に失敗しました: FFmpeg failed",
        ):
            utils.download(
                "test_video",
                str(tmp_path),
                start_time="01:00",
                end_time="02:00",
            )

    assert not output_file.exists()
