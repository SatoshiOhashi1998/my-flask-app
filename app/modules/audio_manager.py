"""
app/modules/audio_manager.py
音楽ファイルの管理・リネームおよびデータベース同期モジュール
"""

import os
import shutil
from typing import Optional, Tuple, List
from app.models import MusicDataModel, db
from app.modules.media_base import is_already_renamed, generate_unique_id

MUSIC_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.aac'}

def is_music_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in MUSIC_EXTENSIONS

def insert_music(music_id: str, original_name: str, new_name: str, path: str):
    music = MusicDataModel(id=music_id, original_name=original_name, new_name=new_name, path=path)
    db.session.add(music)
    db.session.commit()

def find_by_id(music_id: str) -> Optional[MusicDataModel]:
    return MusicDataModel.query.filter_by(id=music_id).first()

def delete_by_id(music_id: str) -> bool:
    music = find_by_id(music_id)
    if not music:
        return False
    db.session.delete(music)
    db.session.commit()
    return True

def rename_single_music_and_save_metadata(file_path: str) -> Optional[Tuple[str, str]]:
    if not os.path.isfile(file_path) or not is_music_file(file_path) or is_already_renamed(os.path.basename(file_path)):
        return None

    ext = os.path.splitext(file_path)[1].lower()
    dir_path = os.path.dirname(file_path)
    original_name = os.path.basename(file_path)

    new_id, new_path = generate_unique_id(dir_path, ext)
    new_name = os.path.basename(new_path)

    shutil.move(file_path, new_path)
    insert_music(new_id, original_name, new_name, new_path)

    return new_name, new_path

def rename_musics_and_save_metadata(directory: str) -> List[str]:
    renamed_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if is_already_renamed(file):
                continue
            file_path = os.path.join(root, file)
            if is_music_file(file_path):
                result = rename_single_music_and_save_metadata(file_path)
                if result:
                    renamed_files.append(result[0])
    return renamed_files

def remove_nonexistent_audio_files_from_db() -> List[str]:
    removed = []
    musics = db.session.query(MusicDataModel).all()
    for music in musics:
        if not os.path.exists(music.path):
            if delete_by_id(music.id):
                removed.append(music.path)
    return removed
