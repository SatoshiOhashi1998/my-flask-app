import os
import locale
import traceback
from flask import Blueprint, request, jsonify
from datetime import datetime

from app.models import db, VideoDataModel, MusicDataModel, Comment
from app.utils import (
    get_video_directories, get_audio_directories, download,
    VIDEO_BASE_PATH, AUDIO_BASE_PATH
)
from app.modules.youtube_api import fetch_youtube_videos, fetch_youtube_video_info
from app.modules.getYouTubeLive import (
    get_archived_live_streams_by_query, get_archived_live_stream_by_videoid
)
from app.modules.video_manager import (
    rename_videos_and_save_metadata, remove_nonexistent_files_from_db, get_video_list_as_string
)
from app.modules.audio_manager import rename_musics_and_save_metadata, remove_nonexistent_audio_files_from_db
from app.modules.export_comments import export_today_comments_to_md
from myutils.markdown.yaml_editor import add_tag_to_markdown
from myutils.markdown.create_dailynote import batch_create_dailies_from_file
from myutils.markdown.fetch_md_file import get_file_content, get_content_by_heading, get_all_yaml_properties, get_yaml_property_value, append_content_to_heading
from myutils.gas_api.use_gas import send_to_gas

api_bp = Blueprint("api", __name__)


# ==========================================
# 1. YouTube ダウンロード・管理関連
# ==========================================

@api_bp.route("/api/youtube/download", methods=["GET", "POST"])
def download_video():
    if request.method == "GET":
        try:
            dir_paths = get_video_directories() + get_audio_directories()
            return jsonify(dir_paths)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "POST":
        data = request.json or {}
        video_id = data.get("video_id")
        save_dir = data.get("save_dir")
        save_quality = data.get("save_quality", "1080")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        download_type = data.get("download_type", "video")

        if not video_id or not save_dir:
            return jsonify({"error": "video_id and save_dir are required"}), 400

        try:
            target_path = download(
                video_id=video_id, save_dir=save_dir, quality=save_quality,
                start_time=start_time, end_time=end_time, download_type=download_type
            )
            return jsonify({
                "response": f"{video_id} のダウンロード（{download_type}）が完了しました",
                "path": target_path
            })
        except Exception as e:
            return jsonify({"error": f"ダウンロードに失敗しました: {str(e)}"}), 500

    return jsonify({"error": "Unsupported method"}), 405


@api_bp.route("/api/reset/media", methods=["GET"])
def reset_medias_id():
    rename_videos_and_save_metadata(VIDEO_BASE_PATH)
    remove_nonexistent_files_from_db()
    rename_musics_and_save_metadata(AUDIO_BASE_PATH)
    remove_nonexistent_audio_files_from_db()
    return jsonify({"response": ""})


# ==========================================
# 2. 動画 (Video) 関連
# ==========================================

@api_bp.route("/api/videos", methods=["GET"])
def get_videos():
    locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")
    videos = db.session.query(VideoDataModel).order_by(VideoDataModel.path).all()
    videos.sort(key=lambda v: (os.path.normpath(os.path.dirname(v.path)), locale.strxfrm(v.original_name)))

    video_data = [
        {
            "id": os.path.splitext(item.new_name)[0],
            "dirpath": os.path.dirname(item.path).split('static')[-1],
            "filename": item.new_name,
            "filetitle": item.original_name,
            "type": "video"
        }
        for item in videos
    ]
    return jsonify({"items": video_data})


@api_bp.route("/api/videos/<video_id>/info", methods=["GET"])
def get_video(video_id):
    video = VideoDataModel.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404
        
    return jsonify({
        "id": video.id,
        "filetitle": video.original_name,
        "dirpath": os.path.dirname(video.path).split('static')[-1],
        "filename": video.new_name,
        "type": "video"
    })


# ==========================================
# 3. 音声・音楽 (Music/Audio) 関連
# ==========================================

@api_bp.route("/api/musics", methods=["GET"])
def get_musics():
    locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")
    musics = db.session.query(MusicDataModel).order_by(MusicDataModel.path).all()
    musics.sort(key=lambda m: (os.path.normpath(os.path.dirname(m.path)), locale.strxfrm(m.original_name)))

    music_data = [
        {
            "id": os.path.splitext(item.new_name)[0],
            "dirpath": os.path.dirname(item.path).split('static')[-1],
            "filename": item.new_name,
            "filetitle": item.original_name,
            "type": "audio"
        }
        for item in musics
    ]
    return jsonify({"items": music_data})


@api_bp.route("/api/musics/<music_id>/info", methods=["GET"])
def get_music(music_id):
    music = MusicDataModel.query.get(music_id)
    if not music:
        return jsonify({"error": "Music not found"}), 404
        
    return jsonify({
        "id": music.id,
        "filetitle": music.original_name,
        "dirpath": os.path.dirname(music.path).split('static')[-1],
        "filename": music.new_name,
        "type": "audio"
    })


# ==========================================
# 4. コメント関連
# ==========================================

@api_bp.route("/api/items/<item_id>/comments", methods=["GET"])
def get_comments(item_id):
    media_type = request.args.get("type", "video")
    comments = Comment.query.filter_by(video_id=item_id, media_type=media_type).order_by(Comment.created_at.desc()).all()
    return jsonify([{
        "id": c.id,
        "content": c.content,
        "media_type": c.media_type,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for c in comments])


@api_bp.route("/api/items/<item_id>/comments", methods=["POST"])
def post_comment(item_id):
    data = request.json
    new_comment = Comment(
        video_id=item_id,
        media_type=data.get("media_type", "video"),
        content=data.get("content")
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"message": "コメントを投稿しました"}), 201


@api_bp.route("/api/comments/<comment_id>", methods=["PUT"])
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.content = request.json.get("content")
    db.session.commit()
    return jsonify({"message": "更新しました"})


@api_bp.route("/api/comments/<comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "削除しました"}), 200


@api_bp.route("/api/comments/export", methods=["GET"])
def export_comment():
    export_today_comments_to_md()
    return jsonify({"message": ""}), 200


# ==========================================
# 5. YouTube API 連携関連
# ==========================================

@api_bp.route('/api/youtube/search', methods=['GET'])
def search_youtube():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'items': []}), 200

    try:
        items = fetch_youtube_videos(query)
        return jsonify({'items': items}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/youtube/<video_id>/info', methods=['GET'])
def get_youtube_info(video_id):
    try:
        video_info = fetch_youtube_video_info(video_id)
        if not video_info:
            return jsonify({'error': 'Video not found'}), 404
        return jsonify(video_info), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==========================================
# 6. Markdown・その他ユーティリティ関連
# ==========================================

@api_bp.route("/api/markdown/create_dailynote", methods=["GET"])
def create_dailynote():
    target_path = os.getenv('DAILY_NOTE_DIR')
    template_path = os.getenv('DAILY_NOTE_TEMPLATE')
    start_date = datetime.now()
    batch_create_dailies_from_file(target_path, start_date, 7, template_path)

    return jsonify({"message": ""}), 200


@api_bp.route("/api/test", methods=["GET"])
def test():
    return jsonify({"message": ""}), 200
