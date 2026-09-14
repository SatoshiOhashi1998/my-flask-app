import os
import glob
from typing import List


APP_BASE_PATH = os.getenv("APP_BASE_PATH", "")

VIDEO_BASE_PATH = os.path.join(
    APP_BASE_PATH,
    "static",
    "video",
)

AUDIO_BASE_PATH = os.path.join(
    APP_BASE_PATH,
    "static",
    "audio",
)

SOUND_FILE_PATH = os.path.join(
    APP_BASE_PATH,
    "static",
    "sound",
)

MEDIA_BASE_PATHS = [
    path.strip()
    for path in os.getenv("MEDIA_BASE_PATHS", "").split("|")
    if path.strip()
]


def get_video_directories(
    base_path: str = VIDEO_BASE_PATH,
) -> List[str]:
    """動画ディレクトリ一覧を取得する。"""
    return [
        d
        for d in glob.glob(os.path.join(base_path, "*"))
        if os.path.isdir(d)
    ]


def get_audio_directories(
    base_path: str = AUDIO_BASE_PATH,
) -> List[str]:
    """音声ディレクトリ一覧を取得する。"""
    return [AUDIO_BASE_PATH] + [
        d
        for d in glob.glob(os.path.join(base_path, "*"))
        if os.path.isdir(d)
    ]


def get_media_directories() -> List[str]:
    """動画・音声などのメディアディレクトリ一覧を取得する。"""
    directories = []

    for base_path in MEDIA_BASE_PATHS:
        if not os.path.isdir(base_path):
            continue

        for root, dirs, _ in os.walk(base_path):
            directories.append(root)

    return directories
