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


def download(video_id: str, save_dir: str, quality: str = "1080",
                   start_time: Optional[str] = None, end_time: Optional[str] = None,
                   trim_overwrite: bool = True) -> None:
    """
    動画をダウンロードして保存。必要に応じてトリミングも実施。

    :param video_id: ダウンロードする動画のIDまたはURL
    :param save_dir: 保存先ディレクトリ
    :param quality: 動画の最大解像度 (例: "1080", "720")
    :param start_time: トリミング開始時間 (例: "00:01:10")
    :param end_time: トリミング終了時間 (例: "00:02:20")
    :param trim_overwrite: Trueなら元動画を上書き、Falseなら別ファイルとして保存
    """

    # URLパラメータを除去
    video_id = video_id.split("&")[0] if "&" in video_id else video_id

    # dlコマンドで動画を一時保存ディレクトリにダウンロード
    temp_dir = VIDEO_BASE_PATH
    command = [
        'dl',
        '-f', f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=mp4]/mp4",
        '-o', f'{temp_dir}/%(title)s.%(ext)s',
        video_id
    ]

    with change_directory(temp_dir):
        subprocess.run(command, check=True)

        # ダウンロードした動画を順番に処理
        for path in glob.glob(os.path.join(temp_dir, "*.mp4")):
            filename = os.path.basename(path)

            # 保存先パス
            target_path = os.path.join(save_dir, filename)

            # トリミング処理
            if start_time and end_time:
                if trim_overwrite:
                    _trim_video(path, None, start_time, end_time, overwrite=True)
                    shutil.move(path, save_dir)
                else:
                    _trim_video(path, target_path, start_time, end_time, overwrite=False)
            else:
                shutil.move(path, save_dir)

            logging.info(f"Downloaded and saved video to {save_dir}")

    # ファイル名のリネーム・DB整理
    rename_videos_and_save_metadata(VIDEO_BASE_PATH)
    remove_nonexistent_files_from_db()


def _trim_video(input_path: str, output_path: Optional[str],
                start_time: str, end_time: str, overwrite: bool = False) -> None:
    """
    動画をトリミングする内部関数

    :param input_path: 元動画パス
    :param output_path: 保存先パス
    :param start_time: 開始時間 hh:mm:ss
    :param end_time: 終了時間 hh:mm:ss
    :param overwrite: Trueなら元動画上書き、Falseなら新規ファイル作成
    """
    if overwrite:
        temp_path = input_path + ".tmp.mp4"
        command = [
            'ffmpeg', '-y', '-i', input_path,
            '-ss', start_time,
            '-to', end_time,
            '-c', 'copy',
            temp_path
        ]
        subprocess.run(command, check=True)
        os.replace(temp_path, input_path)
    else:
        if output_path is None:
            raise ValueError("output_path must be specified when overwrite=False")
        command = [
            'ffmpeg', '-y', '-i', input_path,
            '-ss', start_time,
            '-to', end_time,
            '-c', 'copy',
            output_path
        ]
        subprocess.run(command, check=True)


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
