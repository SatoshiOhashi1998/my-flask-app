import os
import glob
import shutil
import re
import logging
from typing import List, Optional
from contextlib import contextmanager

import yt_dlp
import ffmpeg

from app.models import db
from app.modules.video_manager import rename_videos_and_save_metadata, remove_nonexistent_files_from_db
from app.modules.audio_manager import rename_musics_and_save_metadata, remove_nonexistent_audio_files_from_db

# 環境変数・ディレクトリ定義
APP_BASE_PATH = os.getenv("APP_BASE_PATH", "")
VIDEO_BASE_PATH = os.path.join(APP_BASE_PATH, "static", "video")
AUDIO_BASE_PATH = os.path.join(APP_BASE_PATH, "static", "audio")
SOUND_FILE_PATH = os.path.join(APP_BASE_PATH, "static", "sound")

FFMPEG_PATH = os.getenv('FFMPEG_PATH')
FFMPEG_DIR = os.getenv('FFMPEG_DIR')


def get_video_directories(base_path: str = VIDEO_BASE_PATH) -> List[str]:
    """動画ディレクトリ一覧を取得"""
    return [d for d in glob.glob(os.path.join(base_path, '*')) if os.path.isdir(d)]

def get_audio_directories(base_path: str = AUDIO_BASE_PATH) -> List[str]:
    """音声ディレクトリ一覧を取得"""
    response = [AUDIO_BASE_PATH] + [d for d in glob.glob(os.path.join(base_path, '*')) if os.path.isdir(d)]
    return response


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

    if download_type == "audio":
        bitrate = quality if quality in ["128", "192", "320"] else "192"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'ffmpeg_location': FFMPEG_DIR,
            'outtmpl': os.path.join(VIDEO_BASE_PATH, '%(title)s.%(ext)s'),
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
            'outtmpl': os.path.join(VIDEO_BASE_PATH, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'merge_output_format': 'mp4',
        }

    downloaded_filename = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_id, download=True)
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

    try:
        rename_videos_and_save_metadata(save_dir)
        remove_nonexistent_files_from_db()
        rename_musics_and_save_metadata(save_dir)
        remove_nonexistent_audio_files_from_db()
    except Exception as e:
        print(f"警告: DB更新中にエラーが発生しました: {str(e)}")

    return final_target_path
