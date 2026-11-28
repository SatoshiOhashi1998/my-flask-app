"""汎用データベースCRUD API。

許可したモデルのみを対象にし、モデルごとに作成必須項目と更新可能項目を制限する。
動画・音楽のDELETEはDB上のメタデータのみを削除し、実ファイルは削除しない。
"""

from datetime import datetime
import os
from sqlalchemy.exc import IntegrityError
from flask import request

from app.models import (
    Comment,
    MusicDataModel,
    VideoDataModel,
    Vocabulary,
    db,
)
from app.utils.api_response import error, success


RESOURCE_CONFIG = {
    "videos": {
        "model": VideoDataModel,
        "required": {"id", "new_name", "path", "original_name"},
        "create_fields": {"id", "new_name", "path", "original_name"},
        "update_fields": {"new_name", "path", "original_name"},
        "integer_id": False,
    },
    "musics": {
        "model": MusicDataModel,
        "required": {"id", "new_name", "path", "original_name"},
        "create_fields": {"id", "new_name", "path", "original_name"},
        "update_fields": {"new_name", "path", "original_name"},
        "integer_id": False,
    },
    "comments": {
        "model": Comment,
        "required": {"video_id", "content"},
        "create_fields": {"video_id", "author", "media_type", "content"},
        "update_fields": {"author", "media_type", "content"},
        "integer_id": True,
    },
    "vocabularies": {
        "model": Vocabulary,
        "required": {"word", "meaning"},
        "create_fields": {"word", "meaning", "source", "tag"},
        "update_fields": {
            "word", "meaning", "source", "tag", "last_reviewed_at"
        },
        "integer_id": True,
    },
}


def _serialize(record):
    """SQLAlchemyモデルをJSON化可能な辞書に変換する。"""
    if isinstance(record, (VideoDataModel, MusicDataModel)):
        data = record.to_dict()
        # メディアAPIと同じく、new_name の拡張子を除いた値を公開IDにする。
        data["id"] = os.path.splitext(record.new_name)[0]
        return data

    if isinstance(record, Comment):
        return {
            "id": record.id,
            "video_id": record.video_id,
            "author": record.author,
            "media_type": record.media_type,
            "content": record.content,
            "created_at": (
                record.created_at.isoformat()
                if record.created_at else None
            ),
        }

    if isinstance(record, Vocabulary):
        return {
            "id": record.id,
            "word": record.word,
            "meaning": record.meaning,
            "source": record.source,
            "tag": record.tag,
            "created_at": (
                record.created_at.isoformat()
                if record.created_at else None
            ),
            "last_reviewed_at": (
                record.last_reviewed_at.isoformat()
                if record.last_reviewed_at else None
            ),
        }

    raise TypeError(f"Unsupported model: {type(record).__name__}")


def _media_id(record):
    """メディアAPIで使用する、拡張子なしの公開IDを返す。"""
    return os.path.splitext(record.new_name)[0]


def _find_media_record(model, media_id):
    """メディア公開IDから動画・音楽レコードを検索する。

    通常はDBの主キーとメディア公開IDが一致するため主キー検索を優先し、
    一致しない既存データについては new_name から公開IDを照合する。
    """
    record = db.session.get(model, media_id)
    if record is not None and _media_id(record) == media_id:
        return record, False

    matches = [
        item for item in model.query.all()
        if _media_id(item) == media_id
    ]
    if len(matches) > 1:
        return None, True
    return (matches[0], False) if matches else (None, False)


def _parse_datetime(value, field_name):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be an ISO 8601 string"
        ) from exc


def _validate_payload(data, allowed_fields, required_fields=()):
    if not isinstance(data, dict):
        return None, "リクエストボディはJSONオブジェクトで指定してください"

    unknown = set(data) - allowed_fields
    if unknown:
        return None, f"許可されていない項目です: {', '.join(sorted(unknown))}"

    missing = [
        field for field in required_fields
        if field not in data or data[field] is None
        or (isinstance(data[field], str) and not data[field].strip())
    ]
    if missing:
        return None, f"必須項目が不足しています: {', '.join(sorted(missing))}"

    for field, value in data.items():
        if field == "last_reviewed_at":
            try:
                data[field] = _parse_datetime(value, field)
            except ValueError as exc:
                return None, str(exc)
        elif field in {"id", "new_name", "path", "original_name",
                       "video_id", "author", "media_type", "content",
                       "word", "meaning", "source", "tag"}:
            if value is not None and not isinstance(value, str):
                return None, f"{field} must be a string"

    return data, None


def register_database_routes(api_bp):
    """許可リソースに対する汎用CRUDルートを登録する。"""

    @api_bp.route("/api/database/<resource>", methods=["GET", "POST"])
    def database_collection(resource):
        config = RESOURCE_CONFIG.get(resource)
        if config is None:
            return error("Resource not found", 404)

        model = config["model"]

        if request.method == "GET":
            records = model.query.order_by(model.id.asc()).all()
            return success([_serialize(record) for record in records])

        data, validation_error = _validate_payload(
            request.get_json(silent=True),
            config["create_fields"],
            config["required"],
        )
        if validation_error:
            return error(validation_error, 400)

        try:
            record = model(**data)
            db.session.add(record)
            db.session.commit()
            return success(
                data=_serialize(record),
                message="データを登録しました",
                status_code=201,
            )
        except IntegrityError:
            db.session.rollback()
            return error("同じIDまたは一意制約に違反するデータが存在します", 409)
        except Exception as exc:
            db.session.rollback()
            return error(str(exc), 500)

    @api_bp.route(
        "/api/database/<resource>/<record_id>",
        methods=["GET", "PATCH", "DELETE"],
    )
    def database_item(resource, record_id):
        config = RESOURCE_CONFIG.get(resource)
        if config is None:
            return error("Resource not found", 404)

        model = config["model"]
        if resource in {"videos", "musics"}:
            record, ambiguous = _find_media_record(model, record_id)
            if ambiguous:
                return error(
                    "Media ID is not unique; the record cannot be identified",
                    409,
                )
        else:
            lookup_id = record_id
            if config["integer_id"]:
                try:
                    lookup_id = int(record_id)
                except ValueError:
                    return error("Invalid record ID", 400)
            record = db.session.get(model, lookup_id)

        if record is None:
            return error("Record not found", 404)

        if request.method == "GET":
            return success(_serialize(record))

        if request.method == "DELETE":
            try:
                db.session.delete(record)
                db.session.commit()
                return success(message="データを削除しました")
            except Exception as exc:
                db.session.rollback()
                return error(str(exc), 500)

        data, validation_error = _validate_payload(
            request.get_json(silent=True),
            config["update_fields"],
        )
        if validation_error:
            return error(validation_error, 400)
        if not data:
            return error("更新する項目を指定してください", 400)

        try:
            for field, value in data.items():
                setattr(record, field, value)
            db.session.commit()
            return success(_serialize(record))
        except IntegrityError:
            db.session.rollback()
            return error("一意制約に違反するデータが存在します", 409)
        except Exception as exc:
            db.session.rollback()
            return error(str(exc), 500)
