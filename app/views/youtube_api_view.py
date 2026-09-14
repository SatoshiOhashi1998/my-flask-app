import traceback

from flask import jsonify, request

from app.modules.media_downloader import download
from app.modules.media_paths import get_media_directories
from app.modules.youtube_api import (
    fetch_youtube_video_info,
    fetch_youtube_videos,
)


def register_youtube_routes(api_bp):
    """YouTube関連のAPIルートを登録する。"""

    @api_bp.route("/api/youtube/download", methods=["GET", "POST"])
    def download_video():
        if request.method == "GET":
            try:
                return jsonify(get_media_directories()), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        data = request.json or {}

        video_id = data.get("video_id")
        save_dir = data.get("save_dir")

        if not video_id or not save_dir:
            return jsonify({
                "error": "video_id and save_dir are required"
            }), 400

        try:
            target_path = download(
                video_id=video_id,
                save_dir=save_dir,
                quality=data.get("save_quality", "1080"),
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                download_type=data.get("download_type", "video"),
            )

            return jsonify({
                "message": f"{video_id} のダウンロードが完了しました",
                "path": target_path,
            }), 200

        except Exception as e:
            return jsonify({
                "error": f"ダウンロードに失敗しました: {str(e)}"
            }), 500

    @api_bp.route("/api/youtube/search", methods=["GET"])
    def search_youtube():
        query = request.args.get("q", "")

        if not query:
            return jsonify({"items": []}), 200

        try:
            items = fetch_youtube_videos(query)

            return jsonify({
                "items": items
            }), 200

        except Exception as e:
            traceback.print_exc()

            return jsonify({
                "error": str(e)
            }), 500

    @api_bp.route("/api/youtube/<video_id>/info", methods=["GET"])
    def get_youtube_info(video_id):
        try:
            video_info = fetch_youtube_video_info(video_id)

            if not video_info:
                return jsonify({
                    "error": "Video not found"
                }), 404

            return jsonify(video_info), 200

        except Exception as e:
            traceback.print_exc()

            return jsonify({
                "error": str(e)
            }), 500
