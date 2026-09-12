import os
import shutil
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import yt_dlp
import ffmpeg

from app.models import VideoDataModel, MusicDataModel
from app.modules.media_manager import (
    insert_media,
    remove_nonexistent_files,
)

from app.modules.media_paths import (
    MEDIA_BASE_PATHS,
)

FFMPEG_PATH = os.getenv("FFMPEG_PATH")
FFMPEG_DIR = os.getenv("FFMPEG_DIR")

YOUTUBE_COOKIE_FILE = os.getenv("YOUTUBE_COOKIE_FILE")


def _extract_youtube_video_id(video_id: str) -> str:
    """YouTube URLまたは動画IDから動画IDを取得する。"""

    video_id = video_id.strip()

    # すでに動画IDだけの場合
    if not video_id.startswith(("http://", "https://")):
        return video_id

    parsed = urlparse(video_id)

    # https://www.youtube.com/watch?v=XXXXXXXXXXX
    if parsed.hostname in (
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
    ):
        query = parse_qs(parsed.query)

        if "v" in query and query["v"]:
            return query["v"][0]

    # https://youtu.be/XXXXXXXXXXX
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")

    raise ValueError(
        f"YouTube動画IDを取得できません: {video_id}"
    )


def _validate_download_params(
    video_id: str,
    save_dir: str,
    quality: str,
    start_time: Optional[str],
    end_time: Optional[str],
    download_type: str,
) -> None:
    """download() の引数を検証する。"""

    # video_id
    if not isinstance(video_id, str) or not video_id.strip():
        raise ValueError("video_idは空にできません。")

    # save_dir
    if not isinstance(save_dir, str) or not save_dir.strip():
        raise ValueError("save_dirは空にできません。")

    if os.path.exists(save_dir) and not os.path.isdir(save_dir):
        raise ValueError(
            f"save_dirがディレクトリではありません: {save_dir}"
        )

    # download_type
    if download_type not in ("video", "audio"):
        raise ValueError(
            f"download_typeが不正です: {download_type!r} "
            "(video または audio を指定してください)"
        )

    # quality
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

    # 時刻
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
                "(例: 90、01:30、01:02:30)"
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


def download(
    video_id: str,
    save_dir: str,
    quality: str = "1080",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    trim_overwrite: bool = True,
    download_type: str = "video",
) -> str:
    print("Deno:", shutil.which("deno"))

    _validate_download_params(
        video_id,
        save_dir,
        quality,
        start_time,
        end_time,
        download_type,
    )

    # YouTube URLの場合は動画IDだけを取り出す
    clean_id = _extract_youtube_video_id(video_id)

    os.makedirs(save_dir, exist_ok=True)

    # ファイル名自体は「ID.拡張子」にする（%(id)s.%(ext)s）
    filename_template = "%(id)s.%(ext)s"

    # yt-dlp 共通設定
    common_ydl_opts = {
        "ffmpeg_location": FFMPEG_DIR,
        "outtmpl": os.path.join(save_dir, filename_template),
        "noplaylist": True,
    }

    # Cookieファイルが存在する場合のみ使用
    if YOUTUBE_COOKIE_FILE and os.path.isfile(YOUTUBE_COOKIE_FILE):
        common_ydl_opts["cookiefile"] = YOUTUBE_COOKIE_FILE

    if download_type == "audio":
        bitrate = quality if quality in ["128", "192", "320"] else "192"

        ydl_opts = {
            **common_ydl_opts,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                }
            ],
        }

    else:
        ydl_opts = {
            **common_ydl_opts,
            "format": f"bestvideo[height<={quality}]+bestaudio/best",
            "merge_output_format": "mp4",
        }

    downloaded_filename = None
    original_title = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_id, download=True)
        original_title = info.get("title", "Unknown Title")

        downloaded_filename = ydl.prepare_filename(info)

        if download_type == "audio":
            base, _ = os.path.splitext(downloaded_filename)
            downloaded_filename = base + ".mp3"
        else:
            base, _ = os.path.splitext(downloaded_filename)
            downloaded_filename = base + ".mp4"

    if not downloaded_filename or not os.path.exists(downloaded_filename):
        raise FileNotFoundError(
            "ダウンロードされたファイルが見つかりません。"
        )

    target_filename = downloaded_filename

    if start_time or end_time:
        ext = ".tmp.mp3" if download_type == "audio" else ".tmp.mp4"
        output_file = (
            os.path.splitext(downloaded_filename)[0] + ext
        )

        try:
            stream = ffmpeg.input(
                downloaded_filename,
                ss=start_time,
                to=end_time,
            )

            if download_type == "audio":
                stream = ffmpeg.output(
                    stream,
                    output_file,
                    acodec="libmp3lame",
                )
            else:
                stream = ffmpeg.output(
                    stream,
                    output_file,
                    vcodec="libx264",
                    acodec="aac",
                )

            ffmpeg.run(
                stream,
                overwrite_output=True,
                cmd=FFMPEG_PATH,
            )

            if trim_overwrite:
                os.replace(output_file, downloaded_filename)
            else:
                target_filename = output_file

        except Exception as e:
            if os.path.exists(output_file):
                os.remove(output_file)

            raise RuntimeError(
                f"トリミング処理に失敗しました: {str(e)}"
            )

    final_target_path = os.path.abspath(
        os.path.join(
            save_dir,
            os.path.basename(target_filename),
        )
    )

    if os.path.abspath(target_filename) != final_target_path:
        shutil.move(target_filename, final_target_path)

    # DBへの登録処理
    try:
        new_name = os.path.basename(final_target_path)

        if download_type == "audio":
            remove_nonexistent_files(MusicDataModel)

            insert_media(
                MusicDataModel,
                clean_id,
                original_title,
                new_name,
                final_target_path,
            )

        else:
            remove_nonexistent_files(VideoDataModel)

            insert_media(
                VideoDataModel,
                clean_id,
                original_title,
                new_name,
                final_target_path,
            )

    except Exception as e:
        print(
            f"警告: DB更新中にエラーが発生しました: {str(e)}"
        )

    return final_target_path
