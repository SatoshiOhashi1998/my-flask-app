import os
import shutil
import re
from typing import List, Optional

import ffmpeg

from app.models import VideoDataModel, MusicDataModel
from app.modules.media_manager import (
    insert_media,
    remove_nonexistent_files,
)
from app.modules.youtube_downloader import (
    extract_youtube_video_id,
    validate_download_params,
    download_from_youtube,
)

from app.modules.media_paths import (
    MEDIA_BASE_PATHS,
)

FFMPEG_PATH = os.getenv("FFMPEG_PATH")
FFMPEG_DIR = os.getenv("FFMPEG_DIR")

YOUTUBE_COOKIE_FILE = os.getenv("YOUTUBE_COOKIE_FILE")


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

    validate_download_params(
        video_id,
        save_dir,
        quality,
        start_time,
        end_time,
        download_type,
    )

    clean_id = extract_youtube_video_id(video_id)

    downloaded_filename, original_title = download_from_youtube(
        video_id,
        save_dir,
        quality,
        download_type,
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
