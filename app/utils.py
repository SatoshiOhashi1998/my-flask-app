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
from app.modules.rename_video_files import rename_videos_and_save_metadata, remove_nonexistent_files_from_db

# 環境変数・ディレクトリ定義
APP_BASE_PATH = os.getenv("APP_BASE_PATH", "")
VIDEO_BASE_PATH = os.path.join(APP_BASE_PATH, "static", "video")
SOUND_FILE_PATH = os.path.join(APP_BASE_PATH, "static", "sound")

FFMPEG_PATH = os.getenv('FFMPEG_PATH')
FFMPEG_DIR = os.getenv('FFMPEG_DIR')


def get_video_directories(base_path: str = VIDEO_BASE_PATH) -> List[str]:
    """動画ディレクトリ一覧を取得"""
    return [d for d in glob.glob(os.path.join(base_path, '*')) if os.path.isdir(d)]


def download(
    video_id: str,
    save_dir: str,
    quality: str = "1080",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    trim_overwrite: bool = True
) -> str:
    """
    yt-dlp + ffmpeg-python を使って動画をダウンロード＆トリミング＆保存する
    Windows対応
    """
    # 動画IDのクリーンアップ
    video_id = video_id.split("&")[0] if "&" in video_id else video_id

    ydl_opts = {
        'format': f'bestvideo[height<={quality}]+bestaudio/best',
        'ffmpeg_location': FFMPEG_DIR,
        'outtmpl': os.path.join(VIDEO_BASE_PATH, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'merge_output_format': 'mp4',
    }

    # ダウンロード
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(video_id, download=True)

    # 最新の動画ファイルを取得
    files = glob.glob(os.path.join(VIDEO_BASE_PATH, '*.mp4'))
    if not files:
        raise FileNotFoundError("No mp4 files found in download directory after download")
    filename = max(files, key=os.path.getmtime)
    filename = os.path.abspath(filename)

    # トリミング処理
    if start_time or end_time:
        output_file = (
            os.path.splitext(filename)[0] + (".tmp.mp4" if trim_overwrite else "_trimmed.mp4")
        )
        output_file = os.path.abspath(output_file)
        stream = ffmpeg.input(filename, ss=start_time, to=end_time)
        stream = ffmpeg.output(stream, output_file, vcodec='libx264', acodec='aac', strict='experimental')
        ffmpeg.run(stream, overwrite_output=True, cmd=FFMPEG_PATH)

        if trim_overwrite:
            os.replace(output_file, filename)
        else:
            filename = output_file

    # 保存先に移動
    os.makedirs(save_dir, exist_ok=True)
    target_path = os.path.abspath(os.path.join(save_dir, os.path.basename(filename)))
    shutil.move(filename, target_path)

    # ファイルリネームとDB更新
    rename_videos_and_save_metadata(save_dir)
    remove_nonexistent_files_from_db()

    return target_path
