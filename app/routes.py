"""
Flask アプリケーションのルーティングモジュール

このモジュールは、動画の視聴、ダウンロード、および YouTube ライブストリームの取得を行うためのエンドポイントを提供します。

## 使用方法
各エンドポイントに HTTP リクエストを送信して、対応する処理を実行します。

## エンドポイント一覧

### /watchVideo
- **メソッド:** GET, POST
- **概要:** 動画を視聴するためのページを提供します。
- **GET リクエスト:**
  - クエリパラメータ:
    - v: 動画 ID
    - t: 時間情報
    - filter: フィルターパラメータ
    - mode: モード指定
  - **レスポンス:** `watchVideo.html` テンプレートをレンダリングし、動画情報を JSON データとして埋め込む。
- **POST リクエスト:**
  - フォームデータ:
    - use_dir: 使用するディレクトリ名
  - **レスポンス:** 指定ディレクトリ内の動画パスリストを JSON 形式で返す。

### /downloadVideo
- **メソッド:** GET, POST
- **概要:** 動画をダウンロードするためのページを提供します。
- **GET リクエスト:**
  - **レスポンス:** `downloadVideo.html` テンプレートを返し、ダウンロード用のディレクトリパスを含む。
- **POST リクエスト:**
  - JSON データ:
    - video_id: ダウンロードする動画の ID
    - save_dir: 保存先のディレクトリ
    - save_quality: 保存時の画質
    - start_time: ダウンロード開始時間
    - end_time: ダウンロード終了時間
  - **レスポンス:** ダウンロードが完了したことを示すメッセージを JSON 形式で返す。

### /getYouTubeLive
- **メソッド:** GET, POST
- **概要:** YouTube ライブ配信のアーカイブを取得し、Google Apps Script に送信する。
- **GET リクエスト:**
  - クエリパラメータ:
    - video_id: 指定の動画 ID に対するアーカイブ情報を取得
    - q: 検索クエリを用いたアーカイブ情報の取得
  - **レスポンス:** YouTube のアーカイブデータを Google Apps Script に送信し、処理結果を JSON 形式で返す。

### /api/videos
- **メソッド:** GET
- **概要:** CSV ファイルから VTuber の動画情報を取得する。
- **レスポンス:** JSON 形式の動画データリストを返す。

"""
import os
import json
import pandas as pd
import openpyxl
import csv
from flask import Flask, render_template, request, jsonify, make_response, Blueprint, send_from_directory
from app.utils import get_video_datas, get_all_video_datas, get_video_paths, get_video_directories, download, VIDEO_BASE_PATH
from app.modules.getYouTubeLive import get_archived_live_streams_by_query, get_archived_live_stream_by_videoid, send_to_gas
from app.modules.rename_video_files import rename_videos_and_save_metadata, remove_nonexistent_files_from_db
from app.models import db, VideoDataModel
import unicodedata
import locale


# Blueprintを作成
main = Blueprint('main', __name__)


@main.route('/watchVideo', methods=['GET', 'POST'])
def watch_video():
    if request.method == 'GET':
        v_param = request.args.get('v')
        time_param = request.args.get('t')
        filter_param = request.args.get('filter')
        mode_param = request.args.get('mode')

        locale.setlocale(locale.LC_COLLATE, 'ja_JP.UTF-8')

        videos = (
            db.session.query(VideoDataModel)
            .order_by(VideoDataModel.path)
            .all()
        )
        videos.sort(key=lambda v: locale.strxfrm(v.original_name))

        video_data = []
        for item in videos:
            video_data.append({'dirpath': os.path.dirname(
                item.path), 'filename': item.new_name, 'filetitle': item.original_name, 'last_time': 0, 'memo': ''})

        send_data = {"v": v_param, "t": time_param,
                     'filter': filter_param, 'mode': mode_param, "items": video_data}

        response = make_response(render_template(
            "watchVideo.html", data=send_data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Expires'] = 0
        response.headers['Pragma'] = 'no-cache'
        return response

    elif request.method == 'POST':
        use_dir = request.form['use_dir']
        return jsonify({'response': get_video_paths(use_dir)})


@main.route('/downloadVideo', methods=['GET', 'POST'])
def download_video():
    if request.method == 'GET':
        dir_paths = get_video_directories()
        return jsonify(dir_paths)  # JSONとして返す

    elif request.method == 'POST':
        data = request.json
        video_id = data.get('video_id')
        save_dir = data.get('save_dir')
        save_quality = data.get('save_quality')
        start_time = data.get('start_time')  # 追加
        end_time = data.get('end_time')      # 追加
        print(start_time)
        print(end_time)

        # ダウンロード処理
        download(video_id=video_id, save_dir=save_dir,
                 quality=save_quality, start_time=start_time, end_time=end_time)

        return jsonify({'response': f'{video_id} のダウンロードが完了しました'})


@main.route('/mahjong', methods=['GET', 'POST'])
def mahjong():
    # 環境変数名を正しく指定
    main_data_path = os.getenv('MAIN_DATA')
    versus_two_path = os.getenv('VERSUS_TWO')
    no_tenpai_path = os.getenv('NO_TENPAI')
    deal_in_rate_path = os.getenv('DEAL_IN_RATE')
    hanchan_earnings_path = os.getenv('HANCHAN_EARNINGS')
    riichi_ev_path = os.getenv('RIICHI_EV')
    open_hand_ev_path = os.getenv('OPEN_HAND_EV')

    send_data = {}

    for path, label in zip(
        [main_data_path, versus_two_path, no_tenpai_path, deal_in_rate_path,
            hanchan_earnings_path, riichi_ev_path, open_hand_ev_path],
        ['main_data', 'versus_two', 'no_tenpai', 'deal_in_rate',
            'hanchan_earnings', 'riichi_ev_path', 'open_hand_ev_path']
    ):
        if path:  # Noneチェック
            df = pd.read_csv(path)
            data_json = df.to_dict(orient='records')
            send_data[label] = data_json
        else:
            send_data[label] = []

    # テンプレートに辞書を渡すだけでOK
    return render_template('mahjong.html', data=send_data)


@main.route("/getYouTubeLive", methods=['GET', 'POST'])
def getYouTubeLives():
    id_param = request.args.get('video_id')
    query_param = request.args.get('q')
    print(f"idparam {id_param}")

    if id_param:
        data = get_archived_live_stream_by_videoid(id_param)
        send_to_gas(data)
    elif query_param:
        data = get_archived_live_streams_by_query(query_param)
        send_to_gas(data)
    return jsonify({"response": ""})

# ✅ React のトップページを提供


@main.route("/")
@main.route('/search')
@main.route('/watch')
def serve_react():
    return send_from_directory("static", "react/index.html")


@main.route("/api/videos", methods=["GET"])
def get_videos():
    # CSVファイルのパス
    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__))  # `routes.py` のあるフォルダ
    CSV_PATH = os.path.join(BASE_DIR, "static", "excel", "vtuber_song.csv")

    # CSVファイルを読み込み
    data = []
    with open(CSV_PATH, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        # ヘッダー行をスキップ
        header = next(reader)

        # 必要なデータを読み込む
        for row in reader:
            title = row[0]  # "Video Title"
            channel = row[1]  # "Channel Name"
            published_date = row[2]  # "Published Date"
            url = row[3]  # "URL"

            # 取得したデータをリストに格納
            data.append({
                "Video Title": title,
                "Channel Name": channel,
                "Published Date": published_date,
                "URL": url
            })

    # データを表示して確認
    for entry in data:
        print(entry)

    # 最終的なデータをJSONとして返す
    return jsonify(data)


@main.route("/api/reset/video", methods=["GET"])
def reset_videos():
    rename_videos_and_save_metadata(VIDEO_BASE_PATH)
    remove_nonexistent_files_from_db()
    return jsonify({'response': ''})

@main.route("/api/test", methods=["GET"])
def test():
    videos = VideoDataModel.query.all()
    sorted_videos = VideoDataModel.query.order_by(VideoDataModel.path, VideoDataModel.original_name).all()
    for index, data in enumerate(videos):
        print(f'{index}: {data.original_name}')

    for index, data in enumerate(videos):
        print(f'{index}: {data.original_name}')

    return jsonify({'respose': ''})




