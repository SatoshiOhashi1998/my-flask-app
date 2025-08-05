import os
import shutil
import sqlite3
import threading
import string
import random

from typing import Optional, Tuple, List

# ------------------------
# ✅ 定数とパス設定
# ------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'video_metadata.db')
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}


# ------------------------
# ✅ データベース管理クラス
# ------------------------

class VideoDatabase:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path=DB_PATH):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.db_path = db_path
                cls._instance._init_db()
            return cls._instance

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    original_name TEXT,
                    new_name TEXT,
                    path TEXT
                )
            ''')

    def get_all(self) -> List[Tuple[str, str, str, str]]:
        with self._connect() as conn:
            rows = conn.execute('SELECT id, original_name, new_name, path FROM videos').fetchall()

        return sorted(
            rows,
            key=lambda row: (os.path.dirname(row[3]), row[1])
        )

    def find_by_id(self, video_id: str) -> Optional[Tuple[str, str, str, str]]:
        with self._connect() as conn:
            return conn.execute(
                'SELECT * FROM videos WHERE id = ?', (video_id,)
            ).fetchone()

    def find_by_original_name(self, substring: str) -> List[Tuple[str, str, str, str]]:
        return self._search_by_field('original_name', substring)

    def find_by_path(self, substring: str) -> List[Tuple[str, str, str, str]]:
        return self._search_by_field('path', substring)

    def _search_by_field(self, field: str, substring: str) -> List[Tuple[str, str, str, str]]:
        query = f"SELECT * FROM videos WHERE {field} LIKE ?"
        with self._connect() as conn:
            return conn.execute(query, (f'%{substring}%',)).fetchall()

    def delete_by_id(self, video_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            if not cur.execute('SELECT 1 FROM videos WHERE id = ?', (video_id,)).fetchone():
                return False
            cur.execute('DELETE FROM videos WHERE id = ?', (video_id,))
            conn.commit()
            return True

    def insert(self, video_id: str, original_name: str, new_name: str, path: str):
        with self._connect() as conn:
            conn.execute('''
                INSERT INTO videos (id, original_name, new_name, path)
                VALUES (?, ?, ?, ?)
            ''', (video_id, original_name, new_name, path))
            conn.commit()


# ------------------------
# ✅ ユーティリティ関数群
# ------------------------

def is_video_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in VIDEO_EXTENSIONS


def generate_unique_video_id(dir_path: str, ext: str, length: int = 11) -> Tuple[str, str]:
    chars = string.ascii_letters + string.digits + '-_'
    while True:
        new_id = ''.join(random.choices(chars, k=length))
        new_filename = new_id + ext
        new_path = os.path.join(dir_path, new_filename)
        if not os.path.exists(new_path):
            return new_id, new_path

def is_already_renamed(filename: str) -> bool:
    name, _ = os.path.splitext(filename)
    return len(name) == 11 and all(c in (string.ascii_letters + string.digits + '-_') for c in name)

# ------------------------
# ✅ 単一ファイル処理
# ------------------------

def rename_single_video_and_save_metadata(file_path: str, db: Optional[VideoDatabase] = None) -> Optional[str]:
    if not os.path.isfile(file_path) or not is_video_file(file_path) or is_already_renamed(file_path):
        return None

    ext = os.path.splitext(file_path)[1].lower()
    dir_path = os.path.dirname(file_path)
    original_name = os.path.basename(file_path)

    new_id, new_path = generate_unique_video_id(dir_path, ext)
    new_name = os.path.basename(new_path)

    shutil.move(file_path, new_path)

    (db or VideoDatabase()).insert(new_id, original_name, new_name, new_path)

    return new_name, new_path


# ------------------------
# ✅ 複数ファイル処理
# ------------------------

def rename_videos_and_save_metadata(directory: str, db: Optional[VideoDatabase] = None) -> List[str]:
    renamed_files = []
    db = db or VideoDatabase()

    for root, _, files in os.walk(directory):
        for file in files:
            if is_already_renamed(file):
                continue  # すでにリネーム済みのファイルはスキップ
            file_path = os.path.join(root, file)
            if is_video_file(file_path):
                new_name = rename_single_video_and_save_metadata(file_path, db)
                if new_name:
                    renamed_files.append(new_name)

    return renamed_files


def remove_nonexistent_files_from_db(db: Optional[VideoDatabase] = None) -> List[str]:
    db = db or VideoDatabase()
    removed = []

    for video_id, original_name, new_name, path in db.get_all():
        if not os.path.exists(path):
            if db.delete_by_id(video_id):
                removed.append(path)

    return removed
