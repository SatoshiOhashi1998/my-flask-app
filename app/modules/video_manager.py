"""
app/modules/video_manager.py
動画ファイルの管理・リネームおよびデータベース同期モジュール
"""

"""
app/modules/video_manager.py
動画ファイルの管理・リネームおよびデータベース同期モジュール
"""

import os
import shutil
from typing import Optional, Tuple, List

from app.models import VideoDataModel
from app.modules.media_base import (
    is_already_renamed,
    generate_unique_id,
)
from app.modules.media_manager import (
    insert_media,
    find_by_id as find_media_by_id,
    delete_by_id as delete_media_by_id,
    remove_nonexistent_files,
)


VIDEO_EXTENSIONS = {
    '.mp4',
    '.mov',
    '.avi',
    '.mkv',
    '.webm',
    '.flv',
}


def is_video_file(file_path: str) -> bool:
    return (
        os.path.splitext(file_path)[1].lower()
        in VIDEO_EXTENSIONS
    )


def insert_video(
    video_id: str,
    original_name: str,
    new_name: str,
    path: str,
):
    insert_media(
        VideoDataModel,
        video_id,
        original_name,
        new_name,
        path,
    )


def find_by_id(
    video_id: str,
) -> Optional[VideoDataModel]:
    return find_media_by_id(
        VideoDataModel,
        video_id,
    )


def delete_by_id(
    video_id: str,
) -> bool:
    return delete_media_by_id(
        VideoDataModel,
        video_id,
    )


def update_video(
    video_id: str,
    new_name: str,
    new_path: str,
) -> bool:
    video = find_by_id(video_id)

    if not video:
        return False

    video.new_name = new_name
    video.path = new_path

    from app.models import db

    db.session.commit()

    return True


def rename_single_video_and_save_metadata(
    file_path: str,
) -> Optional[Tuple[str, str]]:
    if (
        not os.path.isfile(file_path)
        or not is_video_file(file_path)
        or is_already_renamed(
            os.path.basename(file_path)
        )
    ):
        return None

    ext = os.path.splitext(file_path)[1].lower()
    dir_path = os.path.dirname(file_path)
    original_name = os.path.basename(file_path)

    new_id, new_path = generate_unique_id(
        dir_path,
        ext,
    )

    new_name = os.path.basename(new_path)

    shutil.move(
        file_path,
        new_path,
    )

    insert_video(
        new_id,
        original_name,
        new_name,
        new_path,
    )

    return new_name, new_path


def rename_videos_and_save_metadata(
    directory: str,
) -> List[str]:
    renamed_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if is_already_renamed(file):
                continue

            file_path = os.path.join(
                root,
                file,
            )

            if is_video_file(file_path):
                result = (
                    rename_single_video_and_save_metadata(
                        file_path
                    )
                )

                if result:
                    renamed_files.append(
                        result[0]
                    )

    return renamed_files


def remove_nonexistent_files_from_db() -> List[str]:
    return remove_nonexistent_files(
        VideoDataModel
    )


def get_video_list_as_string() -> List[str]:
    videos = (
        VideoDataModel.query
        .order_by(VideoDataModel.path)
        .all()
    )

    base_url = os.getenv(
        "USE_URL",
        "",
    )

    return [
        f"[{video.original_name}]"
        f"({base_url}?v={video.new_name})"
        for video in videos
    ]
