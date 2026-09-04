import os
import glob
import shutil
import re
import logging
from typing import List, Optional

import yt_dlp
import ffmpeg

from app.models import VideoDataModel, MusicDataModel
from app.modules.video_manager import insert_video, remove_nonexistent_files_from_db
from app.modules.audio_manager import insert_music, remove_nonexistent_audio_files_from_db
from app.modules.media_manager import (
    insert_media,
    remove_nonexistent_files,
)

# 環境変数・ディレクトリ定義
APP_BASE_PATH = os.getenv("APP_BASE_PATH", "")
VIDEO_BASE_PATH = os.path.join(APP_BASE_PATH, "static", "video")
AUDIO_BASE_PATH = os.path.join(APP_BASE_PATH, "static", "audio")
SOUND_FILE_PATH = os.path.join(APP_BASE_PATH, "static", "sound")

MEDIA_BASE_PATHS = [
    path.strip()
    for path in os.getenv("MEDIA_BASE_PATHS", "").split("|")
    if path.strip()
]

FFMPEG_PATH = os.getenv('FFMPEG_PATH')
FFMPEG_DIR = os.getenv('FFMPEG_DIR')


def get_video_directories(base_path: str = VIDEO_BASE_PATH) -> List[str]:
    """動画ディレクトリ一覧を取得"""
    return [d for d in glob.glob(os.path.join(base_path, '*')) if os.path.isdir(d)]


def get_audio_directories(base_path: str = AUDIO_BASE_PATH) -> List[str]:
    """音声ディレクトリ一覧を取得"""
    response = [AUDIO_BASE_PATH] + [d for d in glob.glob(os.path.join(base_path, '*')) if os.path.isdir(d)]
    return response

def get_media_directories() -> List[str]:
    directories = []

    for base_path in MEDIA_BASE_PATHS:
        if not os.path.isdir(base_path):
            continue

        for root, dirs, _ in os.walk(base_path):
            directories.append(root)

    return directories

def download(
    video_id: str,
    save_dir: str,
    quality: str = "1080",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    trim_overwrite: bool = True,
    download_type: str = "video"
) -> str:
    clean_id = video_id.split("&")[0] if "&" in video_id else video_id

    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(VIDEO_BASE_PATH, exist_ok=True)

    # ファイル名自体は「ID.拡張子」にする（%(id)s.%(ext)s）
    filename_template = '%(id)s.%(ext)s'

    if download_type == "audio":
        bitrate = quality if quality in ["128", "192", "320"] else "192"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'ffmpeg_location': FFMPEG_DIR,
            'outtmpl': os.path.join(VIDEO_BASE_PATH, filename_template),
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': bitrate,
            }],
        }
    else:
        ydl_opts = {
            'format': f'bestvideo[height<={quality}]+bestaudio/best',
            'ffmpeg_location': FFMPEG_DIR,
            'outtmpl': os.path.join(VIDEO_BASE_PATH, filename_template),
            'noplaylist': True,
            'merge_output_format': 'mp4',
        }

    downloaded_filename = None
    original_title = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_id, download=True)
        original_title = info.get('title', 'Unknown Title')
        
        downloaded_filename = ydl.prepare_filename(info)
        
        if download_type == "audio":
            base, _ = os.path.splitext(downloaded_filename)
            downloaded_filename = base + ".mp3"
        else:
            base, _ = os.path.splitext(downloaded_filename)
            downloaded_filename = base + ".mp4"

    if not downloaded_filename or not os.path.exists(downloaded_filename):
        raise FileNotFoundError("ダウンロードされたファイルが見つかりません。")

    target_filename = downloaded_filename

    if start_time or end_time:
        ext = ".tmp.mp3" if download_type == "audio" else ".tmp.mp4"
        output_file = os.path.splitext(downloaded_filename)[0] + ext
        
        try:
            stream = ffmpeg.input(downloaded_filename, ss=start_time, to=end_time)
            if download_type == "audio":
                stream = ffmpeg.output(stream, output_file, acodec='libmp3lame')
            else:
                stream = ffmpeg.output(stream, output_file, vcodec='libx264', acodec='aac')
                
            ffmpeg.run(stream, overwrite_output=True, cmd=FFMPEG_PATH)

            if trim_overwrite:
                os.replace(output_file, downloaded_filename)
            else:
                target_filename = output_file
        except Exception as e:
            if os.path.exists(output_file):
                os.remove(output_file)
            raise RuntimeError(f"トリミング処理に失敗しました: {str(e)}")

    final_target_path = os.path.abspath(os.path.join(save_dir, os.path.basename(target_filename)))
    
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
        print(f"警告: DB更新中にエラーが発生しました: {str(e)}")

    return final_target_path
