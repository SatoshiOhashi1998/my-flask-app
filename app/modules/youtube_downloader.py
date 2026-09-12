import os
from typing import Optional
from urllib.parse import urlparse, parse_qs

import yt_dlp


FFMPEG_DIR = os.getenv("FFMPEG_DIR")
YOUTUBE_COOKIE_FILE = os.getenv("YOUTUBE_COOKIE_FILE")


def extract_youtube_video_id(video_id: str) -> str:
    """YouTube URLまたは動画IDから動画IDを取得する。"""

    video_id = video_id.strip()

    if not video_id.startswith(("http://", "https://")):
        return video_id

    parsed = urlparse(video_id)

    if parsed.hostname in (
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
    ):
        query = parse_qs(parsed.query)

        if "v" in query and query["v"]:
            return query["v"][0]

    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")

    raise ValueError(
        f"YouTube動画IDを取得できません: {video_id}"
    )


def validate_download_params(
    video_id: str,
    save_dir: str,
    quality: str,
    start_time: Optional[str],
    end_time: Optional[str],
    download_type: str,
) -> None:
    """YouTubeダウンロードの引数を検証する。"""

    if not isinstance(video_id, str) or not video_id.strip():
        raise ValueError("video_idは空にできません。")

    if not isinstance(save_dir, str) or not save_dir.strip():
        raise ValueError("save_dirは空にできません。")

    if os.path.exists(save_dir) and not os.path.isdir(save_dir):
        raise ValueError(
            f"save_dirがディレクトリではありません: {save_dir}"
        )

    if download_type not in ("video", "audio"):
        raise ValueError(
            f"download_typeが不正です: {download_type!r} "
            "(video または audio を指定してください)"
        )

    if download_type == "audio":
        if quality not in ("128", "192", "320"):
            raise ValueError(
                f"音声のqualityが不正です: {quality!r} "
                "(128, 192, 320 のいずれかを指定してください)"
            )
    else:
        try:
            quality_value = int(quality)
        except (TypeError, ValueError):
            raise ValueError(
                f"動画のqualityが不正です: {quality!r}"
            )

        if quality_value <= 0:
            raise ValueError(
                f"動画のqualityは正の整数で指定してください: {quality!r}"
            )

    def parse_time(value: Optional[str]) -> Optional[float]:
        if value is None:
            return None

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"時間指定が不正です: {value!r}"
            )

        parts = value.split(":")

        try:
            if len(parts) == 2:
                minutes, seconds = parts
                total = int(minutes) * 60 + float(seconds)

            elif len(parts) == 3:
                hours, minutes, seconds = parts
                total = (
                    int(hours) * 3600
                    + int(minutes) * 60
                    + float(seconds)
                )

            else:
                raise ValueError

        except ValueError:
            raise ValueError(
                f"時間指定の形式が不正です: {value!r} "
                "(例: 01:30、01:02:30)"
            )

        if total < 0:
            raise ValueError(
                f"時間指定は0以上にしてください: {value!r}"
            )

        return total

    start_seconds = parse_time(start_time)
    end_seconds = parse_time(end_time)

    if (
        start_seconds is not None
        and end_seconds is not None
        and start_seconds >= end_seconds
    ):
        raise ValueError(
            "start_timeはend_timeより前に指定してください。"
        )


def _build_common_ydl_options(save_dir: str) -> dict:
    """動画・音声共通のyt-dlpオプションを作成する。"""

    options = {
        "ffmpeg_location": FFMPEG_DIR,
        "outtmpl": os.path.join(
            save_dir,
            "%(id)s.%(ext)s",
        ),
        "noplaylist": True,
    }

    if YOUTUBE_COOKIE_FILE and os.path.isfile(YOUTUBE_COOKIE_FILE):
        options["cookiefile"] = YOUTUBE_COOKIE_FILE

    return options


def _build_ydl_options(
    save_dir: str,
    quality: str,
    download_type: str,
) -> dict:
    """ダウンロード種別に応じたyt-dlpオプションを作成する。"""

    common_options = _build_common_ydl_options(save_dir)

    if download_type == "audio":
        bitrate = (
            quality
            if quality in ("128", "192", "320")
            else "192"
        )

        return {
            **common_options,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                }
            ],
        }

    return {
        **common_options,
        "format": (
            f"bestvideo[height<={quality}]+bestaudio/best"
        ),
        "merge_output_format": "mp4",
    }


def download_from_youtube(
    video_id: str,
    save_dir: str,
    quality: str = "1080",
    download_type: str = "video",
) -> tuple[str, str]:
    """
    YouTubeから動画または音声をダウンロードする。

    Returns:
        tuple[str, str]:
            ダウンロードされたファイルパスと元タイトル。
    """

    clean_id = extract_youtube_video_id(video_id)

    ydl_opts = _build_ydl_options(
        save_dir,
        quality,
        download_type,
    )

    os.makedirs(save_dir, exist_ok=True)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            clean_id,
            download=True,
        )

        original_title = info.get(
            "title",
            "Unknown Title",
        )

        downloaded_filename = ydl.prepare_filename(info)

    if download_type == "audio":
        base, _ = os.path.splitext(downloaded_filename)
        downloaded_filename = base + ".mp3"
    else:
        base, _ = os.path.splitext(downloaded_filename)
        downloaded_filename = base + ".mp4"

    if not os.path.exists(downloaded_filename):
        raise FileNotFoundError(
            "ダウンロードされたファイルが見つかりません。"
        )

    return downloaded_filename, original_title
