"""
app/modules/audio_manager.py
音楽ファイルの管理・リネームおよびデータベース同期モジュール
"""

"""
app/modules/audio_manager.py
音楽ファイルの管理・リネームおよびデータベース同期モジュール
"""

import os
import shutil
from typing import Optional, Tuple, List

from app.models import MusicDataModel
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


MUSIC_EXTENSIONS = {
    '.mp3',
    '.wav',
    '.m4a',
    '.flac',
    '.aac',
}


def is_music_file(file_path: str) -> bool:
    return (
        os.path.splitext(file_path)[1].lower()
        in MUSIC_EXTENSIONS
    )


def insert_music(
    music_id: str,
    original_name: str,
    new_name: str,
    path: str,
):
    insert_media(
        MusicDataModel,
        music_id,
        original_name,
        new_name,
        path,
    )


def find_by_id(
    music_id: str,
) -> Optional[MusicDataModel]:
    return find_media_by_id(
        MusicDataModel,
        music_id,
    )


def delete_by_id(
    music_id: str,
) -> bool:
    return delete_media_by_id(
        MusicDataModel,
        music_id,
    )


def rename_single_music_and_save_metadata(
    file_path: str,
) -> Optional[Tuple[str, str]]:
    if (
        not os.path.isfile(file_path)
        or not is_music_file(file_path)
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

    insert_music(
        new_id,
        original_name,
        new_name,
        new_path,
    )

    return new_name, new_path


def rename_musics_and_save_metadata(
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

            if is_music_file(file_path):
                result = (
                    rename_single_music_and_save_metadata(
                        file_path
                    )
                )

                if result:
                    renamed_files.append(
                        result[0]
                    )

    return renamed_files


def remove_nonexistent_audio_files_from_db() -> List[str]:
    return remove_nonexistent_files(
        MusicDataModel
    )
