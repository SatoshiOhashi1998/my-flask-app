import locale
import os
import traceback
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request

from app.models import Comment, MusicDataModel, VideoDataModel, db
from app.modules.audio_manager import (
    remove_nonexistent_audio_files_from_db,
    rename_musics_and_save_metadata,
)
from app.modules.export_comments import export_today_comments_to_md
from app.modules.getWeatherData import (
    register_today_weather_to_calendar,
    register_tomorrow_weather_to_calendar,
)
from app.modules.use_md_file import (
    create_dailynote,
    export_english_vocabulary,
    export_single_vocabulary,
    register_tasks_by_date,
    test_md,
)
from app.modules.video_manager import (
    remove_nonexistent_files_from_db,
    rename_videos_and_save_metadata,
)
from app.modules.youtube_api import fetch_youtube_video_info, fetch_youtube_videos
from app.utils import (
    AUDIO_BASE_PATH,
    VIDEO_BASE_PATH,
    download,
    get_audio_directories,
    get_video_directories,
)

api_bp = Blueprint("api", __name__)


# ==========================================
# 共通ヘルパー関数
# ==========================================

def _format_media_item(item, media_type: str) -> dict:
    """VideoDataModel / MusicDataModel からレスポンス用辞書を作成"""
    return {
        "id": os.path.splitext(item.new_name)[0],
        "dirpath": os.path.dirname(item.path).split("static")[-1],
        "filename": item.new_name,
        "filetitle": item.original_name,
        "type": media_type,
    }


def _execute_task_sync(target_date: str, start_time: str):
    """タスク同期共通ロジックとレスポンス整形"""
    register_tasks_by_date(
        target_date=target_date,
        start_hour_min=start_time,
        sunday_first=False,
    )
    return jsonify({
        "status": "success",
        "message": f"{target_date} のタスクをGoogleカレンダーに送信しました。",
        "date": target_date,
    }), 200


# ==========================================
# 1. 動画 (Video) 関連
# ==========================================

@api_bp.route("/api/videos", methods=["GET"])
def get_videos():
    locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")
    videos = db.session.query(VideoDataModel).order_by(VideoDataModel.path).all()
    videos.sort(key=lambda v: (os.path.normpath(os.path.dirname(v.path)), locale.strxfrm(v.original_name)))

    return jsonify({"items": [_format_media_item(v, "video") for v in videos]})


@api_bp.route("/api/videos/<video_id>/info", methods=["GET"])
def get_video(video_id):
    video = VideoDataModel.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    return jsonify(_format_media_item(video, "video"))


# ==========================================
# 2. 音声・音楽 (Music/Audio) 関連
# ==========================================

@api_bp.route("/api/musics", methods=["GET"])
def get_musics():
    locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")
    musics = db.session.query(MusicDataModel).order_by(MusicDataModel.path).all()
    musics.sort(key=lambda m: (os.path.normpath(os.path.dirname(m.path)), locale.strxfrm(m.original_name)))

    return jsonify({"items": [_format_media_item(m, "audio") for m in musics]})


@api_bp.route("/api/musics/<music_id>/info", methods=["GET"])
def get_music(music_id):
    music = MusicDataModel.query.get(music_id)
    if not music:
        return jsonify({"error": "Music not found"}), 404

    return jsonify(_format_media_item(music, "audio"))


# ==========================================
# 3. コメント関連
# ==========================================

@api_bp.route("/api/comments/<item_id>", methods=["GET"])
def get_comments(item_id):
    media_type = request.args.get("type", "video")
    comments = (
        Comment.query.filter_by(video_id=item_id, media_type=media_type)
        .order_by(Comment.created_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": c.id,
            "content": c.content,
            "media_type": c.media_type,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for c in comments
    ])


@api_bp.route("/api/comments/<item_id>", methods=["POST"])
def post_comment(item_id):
    data = request.json or {}
    new_comment = Comment(
        video_id=item_id,
        media_type=data.get("media_type", "video"),
        content=data.get("content"),
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"message": "コメントを投稿しました"}), 201


@api_bp.route("/api/comments/<comment_id>", methods=["PUT"])
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.content = (request.json or {}).get("content")
    db.session.commit()
    return jsonify({"message": "コメントを更新しました"}), 200


@api_bp.route("/api/comments/<comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "コメントを削除しました"}), 200


@api_bp.route("/api/comments/export", methods=["GET"])
def export_comment():
    export_today_comments_to_md()
    return jsonify({"message": "本日のコメントを出力しました"}), 200


# ==========================================
# 4. YouTube API 連携・ダウンロード関連
# ==========================================

@api_bp.route("/api/youtube/download", methods=["GET", "POST"])
def download_video():
    if request.method == "GET":
        try:
            dir_paths = get_video_directories() + get_audio_directories()
            return jsonify(dir_paths), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "POST":
        data = request.json or {}
        video_id = data.get("video_id")
        save_dir = data.get("save_dir")

        if not video_id or not save_dir:
            return jsonify({"error": "video_id and save_dir are required"}), 400

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
            return jsonify({"error": f"ダウンロードに失敗しました: {str(e)}"}), 500


@api_bp.route("/api/youtube/search", methods=["GET"])
def search_youtube():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"items": []}), 200

    try:
        items = fetch_youtube_videos(query)
        return jsonify({"items": items}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/youtube/<video_id>/info", methods=["GET"])
def get_youtube_info(video_id):
    try:
        video_info = fetch_youtube_video_info(video_id)
        if not video_info:
            return jsonify({"error": "Video not found"}), 404
        return jsonify(video_info), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ==========================================
# 5. Markdown・ユーティリティ関連
# ==========================================

@api_bp.route("/api/reset/media", methods=["GET"])
def reset_medias_id():
    rename_videos_and_save_metadata(VIDEO_BASE_PATH)
    remove_nonexistent_files_from_db()
    rename_musics_and_save_metadata(AUDIO_BASE_PATH)
    remove_nonexistent_audio_files_from_db()
    return jsonify({"message": "メディアメタデータをリセットしました"}), 200


@api_bp.route("/api/markdown/create_dailynote", methods=["GET"])
def create_dailynotes():
    create_dailynote()
    return jsonify({"message": "デイリーノートを作成しました"}), 200


@api_bp.route("/api/markdown/export_english", methods=["GET"])
def export_english():
    export_english_vocabulary()
    return jsonify({"message": "英単語を出力しました"}), 200


@api_bp.route("/api/markdown/export_vocablary", methods=["GET"])
def export_vocablary():
    export_single_vocabulary()
    return jsonify({"message": "語彙を出力しました"}), 200


@api_bp.route("/api/test", methods=["GET"])
def test():
    test_md()
    return jsonify({"message": "テスト処理を実行しました"}), 200


# ==========================================
# 6. Google Calendar・天気関連
# ==========================================

@api_bp.route("/api/weather/get/today", methods=["GET"])
def register_today_weather():
    register_today_weather_to_calendar()
    return jsonify({"message": "本日の天気情報をカレンダーに登録しました"}), 200


@api_bp.route("/api/weather/get/tomorrow", methods=["GET"])
def register_tomorrow_weather():
    register_tomorrow_weather_to_calendar()
    return jsonify({"message": "翌日の天気情報をカレンダーに登録しました"}), 200


@api_bp.route("/api/calendar/sync-tasks/today", methods=["GET"])
def sync_today_tasks_to_calendar():
    """本日のDaily NoteのタスクをGoogleカレンダーへ送信する"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    start_time = request.args.get("start_time", "09:00")
    return _execute_task_sync(today_str, start_time)


@api_bp.route("/api/calendar/sync-tasks/tomorrow", methods=["GET"])
def sync_tomorrow_tasks_to_calendar():
    """翌日のDaily NoteのタスクをGoogleカレンダーへ送信する"""
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    start_time = request.args.get("start_time", "09:00")
    return _execute_task_sync(tomorrow_str, start_time)


@api_bp.route("/api/calendar/sync-tasks/date", methods=["GET"])
def sync_tasks_by_date_to_calendar():
    """指定日のDaily NoteのタスクをGoogleカレンダーへ送信する"""
    date_str = request.args.get("date")
    start_time = request.args.get("start_time", "09:00")

    if not date_str:
        return jsonify({"status": "error", "message": "クエリパラメータ 'date' (YYYY-MM-DD) は必須です。"}), 400

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"status": "error", "message": "無効な日付フォーマットです。YYYY-MM-DD 形式で指定してください。"}), 400

    return _execute_task_sync(date_str, start_time)
