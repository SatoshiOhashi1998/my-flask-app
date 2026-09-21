import locale
import os

from flask import jsonify, send_from_directory, request

from app.models import MusicDataModel, VideoDataModel, db
from app.media.media_paths import MEDIA_BASE_PATHS
from app.media.audio_manager import (
    remove_nonexistent_audio_files_from_db,
    rename_musics_and_save_metadata,
)
from app.media.video_manager import (
    remove_nonexistent_files_from_db,
    rename_videos_and_save_metadata,
)


def _format_media_item(item, media_type: str) -> dict:
    """メディアモデルをAPIレスポンス形式に変換する。"""
    directory = os.path.dirname(item.path)

    dirpath = directory

    for base_path in MEDIA_BASE_PATHS:
        try:
            relative_path = os.path.relpath(
                directory,
                base_path,
            )

            # base_path自身の場合
            if relative_path == ".":
                dirpath = ""
                break

            # base_path配下の場合
            if (
                not relative_path.startswith("..")
                and not os.path.isabs(relative_path)
            ):
                dirpath = relative_path
                break

        except ValueError:
            # Windowsでドライブが異なる場合など
            continue

    return {
        "id": os.path.splitext(item.new_name)[0],
        "dirpath": dirpath,
        "filename": item.new_name,
        "filetitle": item.original_name,
        "type": media_type,
    }


def register_media_routes(api_bp):
    """動画・音声関連のAPIルートを登録する。"""

    @api_bp.route("/api/videos", methods=["GET"])
    def get_videos():
        locale.setlocale(
            locale.LC_COLLATE,
            "ja_JP.UTF-8",
        )

        videos = (
            db.session
            .query(VideoDataModel)
            .order_by(VideoDataModel.path)
            .all()
        )

        videos.sort(
            key=lambda v: (
                os.path.normpath(
                    os.path.dirname(v.path)
                ),
                locale.strxfrm(v.original_name),
            )
        )

        return jsonify({
            "items": [
                _format_media_item(v, "video")
                for v in videos
            ]
        })

    @api_bp.route("/api/videos/<video_id>/info", methods=["GET"])
    def get_video(video_id):
        video = VideoDataModel.query.get(video_id)

        if not video:
            return jsonify({
                "error": "Video not found"
            }), 404

        return jsonify(
            _format_media_item(video, "video")
        )

    @api_bp.route(
        "/api/videos/<video_id>/stream",
        methods=["GET"],
    )
    def stream_video(video_id):
        video = VideoDataModel.query.get_or_404(
            video_id
        )

        directory = os.path.dirname(video.path)
        filename = video.new_name

        return send_from_directory(
            directory,
            filename,
        )

    @api_bp.route("/api/musics", methods=["GET"])
    def get_musics():
        locale.setlocale(
            locale.LC_COLLATE,
            "ja_JP.UTF-8",
        )

        musics = (
            db.session
            .query(MusicDataModel)
            .order_by(MusicDataModel.path)
            .all()
        )

        musics.sort(
            key=lambda m: (
                os.path.normpath(
                    os.path.dirname(m.path)
                ),
                locale.strxfrm(m.original_name),
            )
        )

        return jsonify({
            "items": [
                _format_media_item(m, "audio")
                for m in musics
            ]
        })

    @api_bp.route(
        "/api/musics/<music_id>/info",
        methods=["GET"],
    )
    def get_music(music_id):
        music = MusicDataModel.query.get(music_id)

        if not music:
            return jsonify({
                "error": "Music not found"
            }), 404

        return jsonify(
            _format_media_item(music, "audio")
        )

    @api_bp.route(
        "/api/musics/<music_id>/stream",
        methods=["GET"],
    )
    def stream_music(music_id):
        music = MusicDataModel.query.get_or_404(
            music_id
        )

        directory = os.path.dirname(music.path)
        filename = music.new_name

        return send_from_directory(
            directory,
            filename,
        )

    @api_bp.route("/api/videos/<video_id>/original-name", methods=["PATCH"])
    def update_video_original_name(video_id):
        data = request.get_json()

        if not data or "original_name" not in data:
            return jsonify({"error": "original_name is required"}), 400

        original_name = data["original_name"]

        if not isinstance(original_name, str) or not original_name.strip():
            return jsonify({"error": "original_name must not be empty"}), 400

        video = db.session.get(VideoDataModel, video_id)

        if video is None:
            return jsonify({"error": "Video not found"}), 404

        video.original_name = original_name
        db.session.commit()

        return jsonify(video.to_dict()), 200


    @api_bp.route("/api/musics/<music_id>/original-name", methods=["PATCH"])
    def update_music_original_name(music_id):
        data = request.get_json()

        if not data or "original_name" not in data:
            return jsonify({"error": "original_name is required"}), 400

        original_name = data["original_name"]

        if not isinstance(original_name, str) or not original_name.strip():
            return jsonify({"error": "original_name must not be empty"}), 400

        music = db.session.get(MusicDataModel, music_id)

        if music is None:
            return jsonify({"error": "Music not found"}), 404

        music.original_name = original_name
        db.session.commit()

        return jsonify(music.to_dict()), 200

    @api_bp.route("/api/reset/media", methods=["GET"])
    def reset_medias_id():
        for base_path in MEDIA_BASE_PATHS:
            rename_videos_and_save_metadata(base_path)
            rename_musics_and_save_metadata(base_path)

        remove_nonexistent_files_from_db()
        remove_nonexistent_audio_files_from_db()

        return jsonify({"message": "メディアメタデータをリセットしました"}), 200
