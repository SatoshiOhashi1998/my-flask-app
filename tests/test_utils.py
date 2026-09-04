import os

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
