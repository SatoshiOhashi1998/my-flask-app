"""
app/modules/media_manager.py
動画・音声で共通して使用するデータベース操作モジュール
"""

import os
from typing import List, Optional, Type

from app.models import db


def insert_media(
    model_class,
    media_id: str,
    original_name: str,
    new_name: str,
    path: str,
):
    media = model_class(
        id=media_id,
        original_name=original_name,
        new_name=new_name,
        path=path,
    )

    db.session.add(media)
    db.session.commit()


def find_by_id(
    model_class,
    media_id: str,
) -> Optional[object]:
    return db.session.get(model_class, media_id)


def delete_by_id(
    model_class,
    media_id: str,
) -> bool:
    media = find_by_id(model_class, media_id)

    if not media:
        return False

    db.session.delete(media)
    db.session.commit()

    return True


def remove_nonexistent_files(
    model_class,
) -> List[str]:
    removed = []

    media_list = db.session.query(model_class).all()

    for media in media_list:
        if not os.path.exists(media.path):
            if delete_by_id(model_class, media.id):
                removed.append(media.path)

    return removed
