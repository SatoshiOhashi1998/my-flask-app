import os
import locale
from flask import Blueprint, render_template, request, make_response, Response, jsonify
import pandas as pd

from app.models import db, VideoDataModel
from app.utils import get_video_directories, get_audio_directories

web = Blueprint("web", __name__)

@web.route("/watchVideo", methods=["GET", "POST"])
def watch_video() -> Response:
    if request.method == "GET":
        v_param = request.args.get("v")
        time_param = request.args.get("t")
        mode_param = request.args.get("mode")

        locale.setlocale(locale.LC_COLLATE, "ja_JP.UTF-8")
        videos = db.session.query(VideoDataModel).order_by(VideoDataModel.path).all()
        videos.sort(key=lambda v: (os.path.normpath(os.path.dirname(v.path)), locale.strxfrm(v.original_name)))

        video_data = [
            {
                "dirpath": os.path.dirname(item.path)[os.path.dirname(item.path).index('static'):],
                "filename": item.new_name,
                "filetitle": item.original_name,
            }
            for item in videos
        ]

        send_data = {
            "items": video_data,
            "settings": {
                "v": v_param or '',
                "t": time_param or 0,
                "mode": mode_param or 'loop',
            }
        }

        response = make_response(render_template("watchVideo.html", data=send_data))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response
    return jsonify({"error": "Unsupported method"}), 405


@web.route("/mahjong", methods=["GET", "POST"])
def mahjong():
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
        "main_data", "versus_two", "no_tenpai", "deal_in_rate",
        "hanchan_earnings", "riichi_ev_path", "open_hand_ev_path",
    ]

    send_data = {}
    for path, label in zip(env_paths, labels):
        if path:
            df = pd.read_csv(path)
            send_data[label] = df.to_dict(orient="records")
        else:
            send_data[label] = []

    return render_template("mahjong.html", data=send_data)