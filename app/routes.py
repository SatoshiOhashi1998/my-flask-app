import os
import locale
import unicodedata
from typing import Dict, Any
import traceback

import pandas as pd
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    make_response,
    Response,
    abort
)

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.utils import (
    get_video_directories,
    get_audio_directories,
    download,
    VIDEO_BASE_PATH
)
from app.modules.getYouTubeLive import (
    get_archived_live_streams_by_query,
    get_archived_live_stream_by_videoid
)
from app.modules.rename_video_files import (
    rename_videos_and_save_metadata,
    remove_nonexistent_files_from_db,
    get_video_list_as_string,
    find_by_id
)


from app.modules.rename_audio_files import rename_musics_and_save_metadata, remove_nonexistent_audio_files_from_db
from app.models import db, VideoDataModel, MusicDataModel, Comment
from myutils.gas_api.use_gas import send_to_gas


main = Blueprint("main", __name__)


@main.route("/watchVideo", methods=["GET", "POST"])
def watch_video() -> Response:
    """動画を視聴するためのページを提供するエンドポイント。

    GET: watchVideo.html をレンダリングし動画データを埋め込む。
    POST: 指定ディレクトリ内の動画パスリストを JSON 形式で返す。
    """
    if request.method == "GET":
        v_param = request.args.get("v")
        time_param = request.args.get("t")
        filter_param = request.args.get("filter")
        mode_param = request.args.get("mode")

        locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")

        videos = db.session.query(VideoDataModel).order_by(
            VideoDataModel.path
        ).all()

        videos.sort(
            key=lambda v: (
                os.path.normpath(os.path.dirname(v.path)),
                locale.strxfrm(v.original_name)
            )
        )

        video_data = [
            {
                "dirpath": os.path.dirname(item.path)[os.path.dirname(item.path).index('static'):],
                "filename": item.new_name,
                "filetitle": item.original_name,
            }
            for item in videos
        ]

        send_data: Dict[str, Any] = {
            "items": video_data,
            "settings": {
                "v": v_param or '',
                "t": time_param or 0,
                "mode": mode_param or 'loop',
            }
        }

        response = make_response(
            render_template("watchVideo.html", data=send_data)
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response
    return jsonify({"error": "Unsupported method"}), 405


@main.route("/downloadVideo", methods=["GET", "POST"])
def download_video() -> Response:
    if request.method == "GET":
        try:
            print(get_audio_directories())
            dir_paths = get_video_directories() + get_audio_directories()
            print(dir_paths)
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
        
        # ★ 追加: ダウンロードのタイプ ('video' または 'audio'。デフォルトは video)
        download_type = data.get("download_type", "video")

        if not video_id or not save_dir:
            return jsonify({"error": "video_id and save_dir are required"}), 400

        try:
            target_path = download(
                video_id=video_id,
                save_dir=save_dir,
                quality=save_quality,
                start_time=start_time,
                end_time=end_time,
                download_type=download_type  # 引数として渡す
            )
            return jsonify({
                "response": f"{video_id} のダウンロード（{download_type}）が完了しました",
                "path": target_path
            })
        except Exception as e:
            return jsonify({"error": f"ダウンロードに失敗しました: {str(e)}"}), 500

    return jsonify({"error": "Unsupported method"}), 405


@main.route("/mahjong", methods=["GET", "POST"])
def mahjong() -> Response:
    """麻雀データを環境変数から読み込み、HTML テンプレートに埋め込む。"""
    env_paths = [
        os.getenv("MAIN_DATA"),
        os.getenv("VERSUS_TWO"),
        os.getenv("NO_TENPAI"),
        os.getenv("DEAL_IN_RATE"),
        os.getenv("HANCHAN_EARNINGS"),
        os.getenv("RIICHI_EV"),
        os.getenv("OPEN_HAND_EV"),
    ]
    labels = [
        "main_data",
        "versus_two",
        "no_tenpai",
        "deal_in_rate",
        "hanchan_earnings",
        "riichi_ev_path",
        "open_hand_ev_path",
    ]

    send_data: Dict[str, Any] = {}
    for path, label in zip(env_paths, labels):
        if path:
            df = pd.read_csv(path)
            send_data[label] = df.to_dict(orient="records")
        else:
            send_data[label] = []

    return render_template("mahjong.html", data=send_data)


@main.route("/getYouTubeLive", methods=["GET", "POST"])
def get_youtube_lives() -> Response:
    """YouTube ライブ配信のアーカイブを取得し GAS に送信する。"""
    id_param = request.args.get("video_id")
    query_param = request.args.get("q")
    GAS_URL = os.getenv("GAS_UTIL_URL")

    if id_param:
        data = get_archived_live_stream_by_videoid(id_param)
        send_to_gas(data, GAS_URL)
    elif query_param:
        data = get_archived_live_streams_by_query(query_param)
        send_to_gas(data, GAS_URL)

    return jsonify({"response": ""})


@main.route("/api/reset/video", methods=["GET"])
def reset_videos() -> Response:
    """動画ファイルのメタデータをリセットし、DB を更新する。"""
    rename_videos_and_save_metadata(VIDEO_BASE_PATH)
    remove_nonexistent_files_from_db()
    return jsonify({"response": ""})


@main.route("/api/info/video", methods=["GET"])
def get_video_info() -> Response:
    for text in get_video_list_as_string():
        print(text)

    return jsonify({"response": "check log"})


@main.route("/api/videos", methods=["GET"])
def get_videos():
    # 検索機能やページネーションを見越して、一旦全ての動画リストをJSONで返す
    locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")

    videos = db.session.query(VideoDataModel).order_by(VideoDataModel.path).all()

    # ソート処理はそのまま活用
    videos.sort(
        key=lambda v: (
            os.path.normpath(os.path.dirname(v.path)),
            locale.strxfrm(v.original_name)
        )
    )

    video_data = [
        {
            # React側で扱いやすいようにIDを付与（filenameをIDとして流用）
            "id": os.path.splitext(item.new_name)[0], 
            "dirpath": os.path.dirname(item.path).split('static')[-1],
            "filename": item.new_name,
            "filetitle": item.original_name,
            "type": "video"
        }
        for item in videos
    ]

    return jsonify({"items": video_data})

@main.route("/api/videos/<video_id>/info", methods=["GET"])
def get_video(video_id):
    video = VideoDataModel.query.get(video_id)
    video = {
        "id": video.id,
        "filetitle": video.original_name, # 表示用のタイトル
        "dirpath": os.path.dirname(video.path).split('static')[-1], # static/ 以下のディレクトリパス
        "filename": video.new_name # ファイル名
    }
    if not video:
        return jsonify({"error": "Video not found"}), 404
    return jsonify(video)


# コメント一覧取得
@main.route("/api/videos/<video_id>/comments", methods=["GET"])
def get_comments(video_id):
    comments = Comment.query.filter_by(video_id=video_id).order_by(Comment.created_at.desc()).all()
    return jsonify([{
        "id": c.id,
        "content": c.content,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for c in comments])

# コメント投稿
@main.route("/api/videos/<video_id>/comments", methods=["POST"])
def post_comment(video_id):
    data = request.json
    new_comment = Comment(
        video_id=video_id,
        content=data.get("content")
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"message": "コメントを投稿しました"}), 201

@main.route("/api/videos/<comment_id>/comments", methods=["PUT"])
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.content = request.json.get("content")
    db.session.commit()
    return jsonify({"message": "更新しました"})

@main.route("/api/videos/<comment_id>/comments", methods=["DELETE"])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "削除しました"}), 200

@main.route("/api/musics", methods=["GET"])
def get_musics():
    locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")
    musics = db.session.query(MusicDataModel).order_by(MusicDataModel.path).all()

    musics.sort(
        key=lambda m: (
            os.path.normpath(os.path.dirname(m.path)),
            locale.strxfrm(m.original_name)
        )
    )

    music_data = [
        {
            "id": os.path.splitext(item.new_name)[0],
            "dirpath": os.path.dirname(item.path).split('static')[-1],
            "filename": item.new_name,
            "filetitle": item.original_name,
            "type": "audio" # フロントのプレイヤー判別用
        }
        for item in musics
    ]

    return jsonify({"items": music_data})

@main.route("/api/musics/<music_id>/info", methods=["GET"])
def get_music(music_id):
    music = MusicDataModel.query.get(music_id)
    if not music:
        return jsonify({"error": "Music not found"}), 404
        
    music_dict = {
        "id": music.id,
        "filetitle": music.original_name,
        "dirpath": os.path.dirname(music.path).split('static')[-1],
        "filename": music.new_name,
        "type": "audio"
    }
    return jsonify(music_dict)

# コメント一覧取得
@main.route("/api/musics/<music_id>/comments", methods=["GET"])
def get_music_comments(music_id):
    comments = Comment.query.filter_by(video_id=music_id).order_by(Comment.created_at.desc()).all()
    return jsonify([{
        "id": c.id,
        "content": c.content,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for c in comments])

# コメント投稿
@main.route("/api/musics/<music_id>/comments", methods=["POST"])
def post_music_comment(music_id):
    data = request.json
    new_comment = Comment(
        video_id=music_id,
        content=data.get("content")
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"message": "コメントを投稿しました"}), 201

@main.route("/api/musics/<comment_id>/comments", methods=["PUT"])
def update_music_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.content = request.json.get("content")
    db.session.commit()
    return jsonify({"message": "更新しました"})

@main.route("/api/musics/<comment_id>/comments", methods=["DELETE"])
def delete_music_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "削除しました"}), 200

@main.route("/test", methods=["GET"])
def test():
    target_path = r"C:\Users\user\PycharmProjects\MyUtilProject\MyApp\FlaskApp\app\static\audio"
    rename_musics_and_save_metadata(target_path)
    remove_nonexistent_audio_files_from_db()
    return jsonify({"message": ""}), 200

@main.route('/api/youtube/search', methods=['GET'])
def search_youtube():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'items': []}), 200

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YOUTUBE_API_KEY is not set.")
        return jsonify({'error': 'YouTube API Key is not configured'}), 500

    try:
        # YouTube APIクライアントの構築
        youtube = build('youtube', 'v3', developerKey=api_key)

        # 検索リクエストの実行
        response = youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            maxResults=45  # フロントの1ページ上限に合わせる
        ).execute()

        items = []
        for item in response.get('items', []):
            # videoIdが存在しないアイテム（チャンネル等）をスキップ
            if 'videoId' not in item.get('id', {}):
                continue

            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            # フロント側のデータ構造（id, filetitle, dirpath, type）に合わせる
            items.append({
                'id': video_id,
                'filetitle': snippet['title'],
                'dirpath': f"YouTube / {snippet['channelTitle']}",
                'thumbnail': snippet['thumbnails']['high']['url'],
                'type': 'youtube'
            })

        return jsonify({'items': items}), 200

    except Exception as e:
        print("=== YouTube API Error Traceback ===")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
