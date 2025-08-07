"""
このモジュールは、Flaskアプリケーションにおけるユーティリティ関数をまとめたものです。

主な機能:
- 動画ファイルのパス取得やダウンロード
- ファイル名のリネーム処理
- 指定したディレクトリ内のファイルの操作
- 音声のみのダウンロード

使用するモジュール:
- glob: パターンマッチングによるファイルパスの取得
- os: オペレーティングシステムの機能へのアクセス
- shutil: 高レベルのファイル操作
- re: 正規表現による文字列操作
- subprocess: 新しいプロセスを生成し、コマンドを実行
- contextlib: コンテキストマネージャの作成
- pathlib: パス操作のためのオブジェクト指向インターフェース
- logging: エラーログの記録

データクラス:
- VideoData: 動画ファイルのディレクトリパスとファイル名を保持するデータクラス。

関数:
- get_video_datas(use_dir: str): 指定されたパス内の動画ファイルパスをJSON形式で取得。
- change_directory(destination: str): 指定したディレクトリに一時的に移動するコンテキストマネージャ。
- get_video_paths(use_path: str): 指定パス内の動画ファイルパスを取得。
- download(video_id: str, save_dir: str, audio_only: bool): 動画または音声をダウンロードし、指定されたディレクトリに保存。
- get_video_directories(): 動画ディレクトリの一覧を取得。
- rename_files(directory: str): 指定ディレクトリ内のファイル名をリネーム。
- rename_files_recursively(root_directory: str): 再帰的にファイルをリネーム。

エラー処理:
- 各関数内で発生する可能性のあるエラーは、適切にキャッチされ、ログに記録されます。特にファイルのリネーム処理では、既に存在するファイル名の重複を確認し、警告をログに記録します。

使用方法:
このモジュールをインポートして、Flaskアプリケーション内でユーティリティ関数を利用してください。必要に応じて、関数のパラメータを変更してカスタマイズしてください。
"""

import glob
import os
import shutil
import re
import subprocess
from contextlib import contextmanager
import logging
from typing import List, Generator, Optional
from dataclasses import dataclass, asdict
from app.models import VideoDataModel, db
from app.modules.rename_video_files import rename_videos_and_save_metadata, remove_nonexistent_files_from_db

APP_BASE_PATH = os.getenv("APP_BASE_PATH")
VIDEO_BASE_PATH = os.path.join(APP_BASE_PATH, "static", "video")
IMAGE_BASE_PATH = os.path.join(APP_BASE_PATH, "static", "image")
IMAGE_ERO_PATH = os.path.join(IMAGE_BASE_PATH, "ero")
SOUND_FILE_PATH = os.path.join(APP_BASE_PATH, "static", "sound")
UNDER_PATH = "*"
ASMR_PATH = os.path.join(VIDEO_BASE_PATH, "asmr")
YOUTUBE_URL_PATTERN = re.compile(r'https://www.youtube.com/watch\?v=.{11}')

@dataclass
class VideoData:
    """動画のデータを扱うクラス"""
    dirpath: str
    filename: str
    last_time: int
    memo: str

def get_all_video_datas(use_dir=VIDEO_BASE_PATH):
    """指定パス内の動画ファイルパスをJSON化したVideoDataのリストとして返す"""
    senddata = []
    

    # 指定ディレクトリ以下のすべての動画ファイルを検索
    for root, dirs, files in os.walk(use_dir):
        for file in files:
            # 動画ファイルの拡張子を確認
            if file.endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv')):  # 必要に応じて拡張子を追加
                video_path = os.path.join(root, file)
                
                # データベースからlast_timeとmemoを取得
                video_data_record = db.session.query(VideoDataModel).filter_by(dirpath=root, filename=file).first()
                
                if video_data_record:
                    # データベースに存在する場合はその値を使用
                    last_time = video_data_record.last_time
                    memo = video_data_record.memo
                else:
                    # 存在しない場合はデフォルト値
                    last_time = 0
                    memo = ""
                
                # VideoDataのインスタンスを作成
                container = VideoData(dirpath=root, filename=file, last_time=last_time, memo=memo)
                senddata.append(asdict(container))

    return senddata

def get_video_datas(use_dir: str = ASMR_PATH) -> List[dict]:
    """指定パス内の動画ファイルパスをJSON化したVideoDataのリストとして返す"""
    video_paths = get_video_paths(use_dir)  # 事前に定義された関数
    senddata = []
    
    # データベースセッションの作成
    for path in video_paths:
        # データベースからlast_timeとmemoを取得
        video_data_record = db.session.query(VideoDataModel).filter_by(dirpath=use_dir, filename=path).first()
        
        if video_data_record:
            # データベースに存在する場合はその値を使用
            last_time = video_data_record.last_time
            memo = video_data_record.memo
        else:
            # 存在しない場合はデフォルト値
            last_time = 0
            memo = ""
        
        # VideoDataのインスタンスを作成
        container = VideoData(dirpath=use_dir, filename=path, last_time=last_time, memo=memo)
        senddata.append(asdict(container))

    return senddata

def add_video_data(video_data: VideoData):
    """VideoDataをデータベースに追加する関数"""
    video_data_model = VideoDataModel(
        dirpath=video_data.dirpath,
        filename=video_data.filename,
        last_time=video_data.last_time,
        memo=video_data.memo
    )
    db.session.add(video_data_model)
    db.session.commit()

@contextmanager
def change_directory(destination: str) -> Generator[None, None, None]:
    """指定したディレクトリに一時的に移動するコンテキストマネージャ"""
    current_directory = os.getcwd()
    try:
        os.chdir(destination)
        yield
    finally:
        os.chdir(current_directory)


def get_video_paths(use_path: str = ASMR_PATH) -> List[str]:
    """指定パス内の動画ファイルパスを取得"""
    video_files = [
        os.path.basename(filepath)
        for extension in ['*.mp4', '*.mkv']
        for filepath in glob.glob(os.path.join(use_path, extension))
    ]
    return video_files


def download(video_id: str, save_dir: str, quality: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> None:
    """
    動画または音声をダウンロードし、保存
    :param video_id: ダウンロードする動画のIDまたはURL
    :param save_dir: 保存先ディレクトリ
    :param quality: 動画の最大解像度 (例: 1080, 720, 480)
    :param start_time: ダウンロード開始時間 (例: "1:14:02")
    :param end_time: ダウンロード終了時間 (例: "1:14:23")
    """
    video_id = video_id.split("&")[0] if "&" in video_id else video_id

    time_section = f"*{start_time}-{end_time}" if start_time and end_time else None
    
    command = [
        'dl',
        '-f', f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=mp4]/mp4",  # mp4形式の最適な動画と音声
        '-o', f'{save_dir}/%(title)s.%(ext)s',  # 出力ファイルパス
    ]
    
    if time_section:
        command.extend(['--download-sections', time_section])
    
    command.append(video_id)

    with change_directory(VIDEO_BASE_PATH):
        popen = subprocess.Popen(command)
        popen.wait()

        rename_files(VIDEO_BASE_PATH)
        for path in glob.glob(os.path.join(VIDEO_BASE_PATH, "*.mp4")):
            shutil.move(new_path, save_dir)
            logging.info(f"Downloaded and moved video to {save_dir}")

    rename_videos_and_save_metadata(VIDEO_BASE_PATH)
    remove_nonexistent_files_from_db()


def get_video_directories() -> List[str]:
    """動画ディレクトリ一覧を取得"""
    return [dirpath for dirpath in glob.glob(os.path.join(VIDEO_BASE_PATH, UNDER_PATH)) if os.path.isdir(dirpath)]


def rename_files(directory: str) -> None:
    """指定ディレクトリ内のファイル名をリネーム"""
    for filename in os.listdir(directory):
        if filename.endswith(".mp4"):
            try:
                new_filename = re.sub(r'\[.*?\]', '', filename)
                new_filename = re.sub(r'[#＃\'’]', '', new_filename).strip()

                if new_filename != filename:
                    new_path = os.path.join(directory, new_filename)
                    old_path = os.path.join(directory, filename)

                    if not os.path.exists(new_path):
                        os.rename(old_path, new_path)
                        logging.info(f"Renamed {filename} to {new_filename}")
                    else:
                        logging.warning(f"File {new_filename} already exists, skipping...")
                else:
                    logging.info(f"No special characters in {filename}, skipping...")
            except Exception as e:
                logging.error(f"Error renaming {filename}: {e}")


def rename_files_recursively(root_directory: str) -> None:
    """再帰的にファイルをリネーム"""
    for root, dirs, _ in os.walk(root_directory):
        for directory in dirs:
            rename_files(os.path.join(root, directory))

if __name__ == '__main__':
    response = get_video_datas()
    print(response)
