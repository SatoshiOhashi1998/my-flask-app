import os
import locale
import unicodedata
from typing import Dict, Any

import pandas as pd
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    make_response,
    Response
)

from app.utils import (
    get_video_directories,
    download,
    VIDEO_BASE_PATH
)
from app.modules.getYouTubeLive import (
    get_archived_live_streams_by_query,
    get_archived_live_stream_by_videoid
)
from app.modules.rename_video_files import (
    rename_videos_and_save_metadata,
    remove_nonexistent_files_from_db
)
from app.models import db, VideoDataModel
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
                "dirpath": os.path.dirname(item.path),
                "filename": item.new_name,
                "filetitle": item.original_name,
            }
            for item in videos
        ]
        print(f'video_data[0]: {video_data[0]}')

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
    """動画をダウンロードするためのエンドポイント。

    GET: 保存先ディレクトリの一覧を返す。
    POST: 指定動画をダウンロードし JSON レスポンスを返す。
    """
    if request.method == "GET":
        dir_paths = get_video_directories()
        return jsonify(dir_paths)

    if request.method == "POST":
        data = request.json or {}
        video_id = data.get("video_id")
        save_dir = data.get("save_dir")
        save_quality = data.get("save_quality")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        download(
            video_id=video_id,
            save_dir=save_dir,
            quality=save_quality,
            start_time=start_time,
            end_time=end_time
        )

        return jsonify({"response": f"{video_id} のダウンロードが完了しました"})

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

    if id_param:
        data = get_archived_live_stream_by_videoid(id_param)
        send_to_gas(data)
    elif query_param:
        data = get_archived_live_streams_by_query(query_param)
        send_to_gas(data)

    return jsonify({"response": ""})


@main.route("/api/reset/video", methods=["GET"])
def reset_videos() -> Response:
    """動画ファイルのメタデータをリセットし、DB を更新する。"""
    rename_videos_and_save_metadata(VIDEO_BASE_PATH)
    remove_nonexistent_files_from_db()
    return jsonify({"response": ""})


@main.route("/api/test", methods=["GET"])
def test() -> Response:
    """テストコード"""
    videos = VideoDataModel.query.all()
    sorted_videos = VideoDataModel.query.order_by(
        VideoDataModel.path, VideoDataModel.original_name
    ).all()

    for index, data in enumerate(videos):
        print(f"{index}: {data.original_name}")

    return jsonify({"response": ""})
