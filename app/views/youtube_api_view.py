import traceback

from flask import request

from app.media.media_downloader import download
from app.media.media_paths import get_media_directories
from app.youtube.youtube_api import (
    fetch_youtube_video_info,
    fetch_youtube_videos,
)
from app.utils.api_response import success, error


def register_youtube_routes(api_bp):
    """YouTube関連のAPIルートを登録する。"""

    @api_bp.route("/api/youtube/download", methods=["GET", "POST"])
    def download_video():
        if request.method == "GET":
            try:
                return success(get_media_directories())

            except Exception as e:
                return error(str(e), 500)

        data = request.json or {}

        video_id = data.get("video_id")
        save_dir = data.get("save_dir")

        if not video_id or not save_dir:
            return error(
                "video_id and save_dir are required",
                400,
            )

        try:
            target_path = download(
                video_id=video_id,
                save_dir=save_dir,
                quality=data.get("save_quality", "1080"),
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                download_type=data.get("download_type", "video"),
            )

            return success(
                data={
                    "path": target_path,
                },
                message=f"{video_id} のダウンロードが完了しました",
            )

        except Exception as e:
            return error(
                f"ダウンロードに失敗しました: {str(e)}",
                500,
            )

    @api_bp.route("/api/youtube/search", methods=["GET"])
    def search_youtube():
        query = request.args.get("q", "")

        if not query:
            return success([])

        try:
            items = fetch_youtube_videos(query)

            return success(items)

        except Exception as e:
            traceback.print_exc()

            return error(str(e), 500)

    @api_bp.route("/api/youtube/<video_id>/info", methods=["GET"])
    def get_youtube_info(video_id):
        try:
            video_info = fetch_youtube_video_info(video_id)

            if not video_info:
                return error("Video not found", 404)

            return success(video_info)

        except Exception as e:
            traceback.print_exc()

            return error(str(e), 500)
