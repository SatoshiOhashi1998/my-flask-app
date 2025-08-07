import os
import shutil
import string
import random
from typing import Optional, Tuple, List

from flask import current_app
from app.models import VideoDataModel, db

# 定数
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}


def is_video_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in VIDEO_EXTENSIONS


def is_already_renamed(filename: str) -> bool:
    name, _ = os.path.splitext(filename)
    allowed_chars = string.ascii_letters + string.digits + '-_'
    return len(name) == 11 and all(c in allowed_chars for c in name)


def generate_unique_video_id(dir_path: str, ext: str, length: int = 11) -> Tuple[str, str]:
    chars = string.ascii_letters + string.digits + '-_'
    while True:
        new_id = ''.join(random.choices(chars, k=length))
        new_filename = new_id + ext
        new_path = os.path.join(dir_path, new_filename)
        if not os.path.exists(new_path):
            return new_id, new_path


# --- DB操作関数 ---

def insert_video(video_id: str, original_name: str, new_name: str, path: str):
    video = VideoDataModel(id=video_id, original_name=original_name, new_name=new_name, path=path)
    db.session.add(video)
    db.session.commit()


def get_all_videos() -> List[VideoDataModel]:
    return VideoDataModel.query.order_by(VideoDataModel.path, VideoDataModel.original_name).all()


def find_by_id(video_id: str) -> Optional[VideoDataModel]:
    return VideoDataModel.query.filter_by(id=video_id).first()


def delete_by_id(video_id: str) -> bool:
    video = find_by_id(video_id)
    if not video:
        return False
    db.session.delete(video)
    db.session.commit()
    return True


def update_video(video_id: str, new_name: str, new_path: str) -> bool:
    video = find_by_id(video_id)
    if not video:
        return False
    video.new_name = new_name
    video.path = new_path
    db.session.commit()
    return True


# --- ファイル操作関数 ---


def rename_single_video_and_save_metadata(file_path: str) -> Optional[Tuple[str, str]]:
    print("rename_single_video_and_save_metadata")
    if (not os.path.isfile(file_path) or
        not is_video_file(file_path) or
        is_already_renamed(os.path.basename(file_path))):
        return None

    ext = os.path.splitext(file_path)[1].lower()
    dir_path = os.path.dirname(file_path)
    original_name = os.path.basename(file_path)

    new_id, new_path = generate_unique_video_id(dir_path, ext)
    new_name = os.path.basename(new_path)

    shutil.move(file_path, new_path)

    # Flaskのアプリコンテキスト内でDB操作
    insert_video(new_id, original_name, new_name, new_path)

    return new_name, new_path


def rename_videos_and_save_metadata(directory: str) -> List[str]:
    print('rename_videos_and_save_metadata')
    renamed_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if is_already_renamed(file):
                continue
            file_path = os.path.join(root, file)
            if is_video_file(file_path):
                result = rename_single_video_and_save_metadata(file_path)
                if result:
                    renamed_files.append(result[0])  # new_nameだけ追加

    return renamed_files


def remove_nonexistent_files_from_db() -> List[str]:
    print('remove_nonexistent_files_from_db')
    removed = []

    videos = get_all_videos()
    for video in videos:
        if not os.path.exists(video.path):
            if delete_by_id(video.id):
                removed.append(video.path)

    return removed


def restore_video_filenames_from_db(update_db: bool = False) -> List[Tuple[str, str]]:
    print("restore_video_filenames_from_db")
    """
    DBに登録されている動画の新しいファイル名を元の名前に戻す。

    Args:
        update_db (bool): DB上のnew_name, pathも更新するか。

    Returns:
        List of tuples (old_path, restored_path)
    """
    restored_files = []

    videos = get_all_videos()
    for video in videos:
        if not os.path.exists(video.path):
            continue

        dir_path = os.path.dirname(video.path)
        restored_path = os.path.join(dir_path, video.original_name)

        if os.path.basename(video.path) == video.original_name:
            continue

        if os.path.exists(restored_path):
            current_app.logger.warning(f"スキップ: {restored_path} は既に存在します")
            continue

        shutil.move(video.path, restored_path)
        restored_files.append((video.path, restored_path))

        if update_db:
            update_video(video.id, video.original_name, restored_path)

    return restored_files
