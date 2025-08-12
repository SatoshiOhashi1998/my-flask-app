"""
YouTubeアーカイブライブ配信情報取得・送信プログラム

このプログラムはYouTube Data APIを利用して、YouTubeからアーカイブされたライブ配信情報を取得し、
Google Apps Script（GAS）に送信する機能を提供します。

主な機能：
1. キーワード検索を利用したアーカイブライブ配信の取得（`get_archived_live_streams_by_query`関数）
2. チャンネルIDに基づいたアーカイブライブ配信の取得（`get_archived_live_streams_by_channelid`関数）
3. ビデオIDに基づいたアーカイブライブ配信の取得（`get_archived_live_stream_by_videoid`関数）
4. 取得した配信情報をJSON形式でGASに送信（`send_to_gas`関数）
5. ExcelファイルからチャンネルIDリストを取得（`get_channel_ids_from_excel`関数）

環境変数：
- `YOUTUBE_API_KEY`: YouTube Data APIキー
- `GAS_YouTube_URL`: Google Apps ScriptのエンドポイントURL

必要なライブラリ：
- `os`, `requests`, `json`, `time`, `datetime`, `timedelta`, `pytz`, `isodate`, `pandas`

関数：

get_archived_live_streams_by_query(query, published_after=None, published_before=None)
    指定されたキーワードでアーカイブライブ配信を検索し、配信タイトル、開始時間、終了時間、説明を含むリストを返します。
    引数:
    - query: 検索キーワード（必須）
    - published_after: 開始日（オプション、デフォルトは7日前）
    - published_before: 終了日（オプション、デフォルトは現在時刻）

get_archived_live_streams_by_channelid(channel_ids, published_after=None, published_before=None)
    指定されたチャンネルIDのリストに基づいてアーカイブライブ配信を取得し、情報リストを返します。
    引数:
    - channel_ids: チャンネルIDのリスト（必須）
    - published_after: 開始日（オプション）
    - published_before: 終了日（オプション）

get_archived_live_stream_by_videoid(video_id)
    特定のビデオIDに基づいてアーカイブライブ配信の情報を取得します。
    引数:
    - video_id: ビデオID（必須）
    戻り値: 取得した配信情報を含む辞書

send_to_gas(data)
    JSON形式で指定されたデータをGASに送信します。
    引数:
    - data: GASに送信するデータ（リスト形式）

get_channel_ids_from_excel()
    指定されたExcelファイルからチャンネルIDのリストを取得し返します。
    戻り値: チャンネルIDのリスト

使用方法：
1. 必要な環境変数（`YOUTUBE_API_KEY`と`GAS_YouTube_URL`）を設定します。
2. `get_archived_live_streams_by_query`, `get_archived_live_streams_by_channelid`または`get_archived_live_stream_by_videoid`を使用してアーカイブされたライブストリーム情報を取得します。
3. `send_to_gas`関数を呼び出し、取得したデータをGASに送信します。

例:
```python
if __name__ == "__main__":
    target_date = '2024-10-27T20:00:00Z'
    
    # チャンネルIDに基づく例
    channel_ids = get_channel_ids_from_excel()
    archived_streams = get_archived_live_streams_by_channelid(channel_ids, published_after=target_date)
    send_to_gas(archived_streams)

    # キーワードに基づく例
    archived_streams = get_archived_live_streams_by_query('#にじ遊戯王祭2024', published_after=target_date)
    send_to_gas(archived_streams)

    # ビデオIDに基づく例
    video_id = "RNQs6Abec3I"
    archived_streams = get_archived_live_stream_by_videoid(video_id)
    send_to_gas(archived_streams)
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
import pytz
import isodate  # ISO 8601形式のdurationを解析するためのライブラリ
import pandas as pd

from myutils.youtube_api.fetch_youtube_data import YouTubeAPI


def get_archived_live_streams_by_query(query, published_after=None, published_before=None):
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    SEARCH_API_URL = 'https://www.googleapis.com/youtube/v3/search'
    VIDEOS_API_URL = 'https://www.googleapis.com/youtube/v3/videos'

    archived_streams = []

    # 引数が指定されていない場合はデフォルト値を設定
    if published_after is None:
        published_after = (datetime.utcnow() - timedelta(days=7)
                           ).isoformat() + 'Z'  # デフォルトは7日前
    if published_before is None:
        published_before = datetime.utcnow().isoformat() + 'Z'  # デフォルトは現在時刻

    search_params = {
        'key': API_KEY,
        'q': query,
        'part': 'snippet',
        'order': 'date',
        'type': 'video',
        'eventType': 'completed',
        'publishedAfter': published_after,  # 引数で指定した開始日
        'publishedBefore': published_before,  # 引数で指定した終了日
        'maxResults': 50
    }

    search_response = requests.get(SEARCH_API_URL, params=search_params)
    archived_events = search_response.json().get('items', [])

    time.sleep(1)

    for event in archived_events:
        video_id = event['id']['videoId']
        channel_title = event['snippet']['channelTitle']

        video_params = {
            'key': API_KEY,
            'id': video_id,
            'part': 'contentDetails'
        }

        video_response = requests.get(VIDEOS_API_URL, params=video_params)
        video_details = video_response.json().get('items', [])

        if video_details:
            duration = video_details[0]['contentDetails'].get(
                'duration', 'PT0S')
            published_at = event['snippet']['publishedAt']
            utc_time = datetime.fromisoformat(published_at[:-1])
            end_time = utc_time.replace(tzinfo=pytz.utc)
            duration_timedelta = isodate.parse_duration(duration)
            start_time = end_time - duration_timedelta

            # JST（日本標準時）に変換
            jst_start_time = start_time.astimezone(pytz.timezone('Asia/Tokyo'))
            jst_end_time = end_time.astimezone(pytz.timezone('Asia/Tokyo'))

            stream_url = f'https://www.youtube.com/watch?v={video_id}'

            archived_streams.append({
                'title': "配信: " + event['snippet']['title'],  # 配信タイトル
                'start': jst_start_time.isoformat(),  # 配信の開始時間
                'end': jst_end_time.isoformat(),  # 配信の終了時間
                # 説明文
                'description': f"配信元: {channel_title}\nリンク: {stream_url}"
            })

        time.sleep(1)

    return archived_streams


def get_archived_live_streams_by_channelid(channel_ids, published_after=None, published_before=None):
    yt_api = YouTubeAPI()

    archived_streams = []

    if published_after is None:
        published_after = datetime.utcnow() - timedelta(days=1)

    if published_before is None:
        published_before = datetime.utcnow()

    # APIの日時指定はISOフォーマット文字列でZ付きで渡す
    published_after_str = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")
    published_before_str = published_before.strftime("%Y-%m-%dT%H:%M:%SZ")

    for channel_id in channel_ids:
        next_page_token = None
        while True:
            response = yt_api.call_api(
                "search", "list",
                part="snippet",
                channelId=channel_id,
                order="date",
                type="video",
                eventType="completed",
                publishedAfter=published_after_str,
                publishedBefore=published_before_str,
                maxResults=10,
                pageToken=next_page_token
            )

            items = response.get("items", [])
            if not items:
                break

            for event in items:
                video_id = event["id"]["videoId"]
                channel_title = event["snippet"]["channelTitle"]

                # 動画の詳細情報取得
                video_details_resp = yt_api.call_api(
                    "videos", "list",
                    part="contentDetails",
                    id=video_id
                )
                video_items = video_details_resp.get("items", [])
                if not video_items:
                    continue

                duration_iso = video_items[0]["contentDetails"].get(
                    "duration", "PT0S")
                published_at = event["snippet"]["publishedAt"]
                utc_time = datetime.fromisoformat(
                    published_at[:-1])  # 'Z'を除去してISO形式に
                end_time = utc_time.replace(tzinfo=pytz.utc)
                duration_timedelta = isodate.parse_duration(duration_iso)
                start_time = end_time - duration_timedelta

                # JSTに変換
                jst_tz = pytz.timezone("Asia/Tokyo")
                jst_start_time = start_time.astimezone(jst_tz)
                jst_end_time = end_time.astimezone(jst_tz)

                stream_url = f"https://www.youtube.com/watch?v={video_id}"

                archived_streams.append({
                    "title": "配信: " + event["snippet"]["title"],
                    "start": jst_start_time.isoformat(),
                    "end": jst_end_time.isoformat(),
                    "description": f"配信元: {channel_title}\nリンク: {stream_url}",
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

            time.sleep(1)  # API制限対策

        time.sleep(1)  # API制限対策

    return archived_streams


def get_archived_live_stream_by_videoid(video_id):
    print(f"get_archived_live_stream_by_videoid")
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    VIDEOS_API_URL = 'https://www.googleapis.com/youtube/v3/videos'

    # 動画情報取得リクエスト
    video_params = {
        'key': API_KEY,
        'id': video_id,
        'part': 'snippet,contentDetails'
    }

    video_response = requests.get(VIDEOS_API_URL, params=video_params)
    video_data = video_response.json().get('items', [])

    if not video_data:
        return {"error": "Video not found or is not an archived live stream"}

    video_info = video_data[0]
    duration = video_info['contentDetails'].get('duration', 'PT0S')
    published_at = video_info['snippet']['publishedAt']
    title = video_info['snippet']['title']
    channel_title = video_info['snippet']['channelTitle']

    # 配信の終了時間 (UTC)
    end_time = datetime.fromisoformat(
        published_at[:-1]).replace(tzinfo=pytz.utc)
    duration_timedelta = isodate.parse_duration(duration)
    start_time = end_time - duration_timedelta

    # JST（日本標準時）に変換
    jst_start_time = start_time.astimezone(pytz.timezone('Asia/Tokyo'))
    jst_end_time = end_time.astimezone(pytz.timezone('Asia/Tokyo'))

    stream_url = f'https://www.youtube.com/watch?v={video_id}'

    return [{
        'title': "配信: " + title,  # 配信タイトル
        'start': jst_start_time.isoformat(),  # 配信の開始時間
        'end': jst_end_time.isoformat(),  # 配信の終了時間
        'description': f"配信元: {channel_title}\nリンク: {stream_url}"  # 説明文
    }]


def get_archived_live_streams_by_playlistid(playlist_id):
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    PLAYLIST_ITEMS_API_URL = 'https://www.googleapis.com/youtube/v3/playlistItems'
    VIDEOS_API_URL = 'https://www.googleapis.com/youtube/v3/videos'

    archived_streams = []
    next_page_token = None

    while True:
        params = {
            'key': API_KEY,
            'playlistId': playlist_id,
            'part': 'snippet',
            'maxResults': 50,
            'pageToken': next_page_token
        }

        response = requests.get(PLAYLIST_ITEMS_API_URL, params=params)
        result = response.json()

        items = result.get('items', [])
        video_ids = [item['snippet']['resourceId']['videoId']
                     for item in items]

        for video_id in video_ids:
            video_params = {
                'key': API_KEY,
                'id': video_id,
                'part': 'snippet,contentDetails'
            }

            video_response = requests.get(VIDEOS_API_URL, params=video_params)
            video_details = video_response.json().get('items', [])

            if video_details:
                detail = video_details[0]
                title = "配信: " + detail['snippet']['title']
                published_at = detail['snippet']['publishedAt']
                channel_title = detail['snippet']['channelTitle']
                duration = detail['contentDetails'].get('duration', 'PT0S')

                utc_time = datetime.fromisoformat(published_at[:-1])
                end_time = utc_time.replace(tzinfo=pytz.utc)
                duration_timedelta = isodate.parse_duration(duration)
                start_time = end_time - duration_timedelta

                jst_start_time = start_time.astimezone(
                    pytz.timezone('Asia/Tokyo'))
                jst_end_time = end_time.astimezone(pytz.timezone('Asia/Tokyo'))

                stream_url = f'https://www.youtube.com/watch?v={video_id}'

                archived_streams.append({
                    'title': title,
                    'start': jst_start_time.isoformat(),
                    'end': jst_end_time.isoformat(),
                    'description': f"配信元: {channel_title}\nリンク: {stream_url}"
                })

            time.sleep(1)

        next_page_token = result.get('nextPageToken')
        if not next_page_token:
            break

    return archived_streams


def send_to_gas(data):
    GAS_ENDPOINT_URL = os.getenv("GAS_YouTube_URL")
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    request_data = {'action': 'addEvent', 'data': data}
    print(request_data)

    response = requests.post(GAS_ENDPOINT_URL, headers=headers, data=json.dumps(
        request_data, ensure_ascii=False).encode('utf-8'))

    if response.status_code == 200:
        print("データの送信に成功しました。")
        print("GASからのレスポンス:", response.text)
    else:
        print(f"エラーが発生しました: {response.status_code} - {response.text}")


def get_channel_ids_from_excel():
    """
    チャンネルIDをまとめているExcelファイルからデータを取得。チャンネルIDのリストを返す。
    """
    CSV_PATH = os.getenv('CHANNEL_CSV_PATH')
    sheet_name = 'データ'                 # シート名
    table_name = 'チャンネルID'            # テーブル名
    # Excelファイルを読み込み
    excel_data = pd.read_excel(CSV_PATH, sheet_name=sheet_name)

    # 列名を表示
    print("列名:", excel_data.columns.tolist())  # ここで列名を確認

    # テーブルから指定された条件に一致するchannelIdを取得
    channel_ids = excel_data[(excel_data['favorite'] == 1)
                             ]['channelId'].tolist()

    return channel_ids


def send_archived_streams_from_excel_channels():
    channel_ids = get_channel_ids_from_excel()
    archived_streams = get_archived_live_streams_by_channelid(channel_ids, published_after, published_before)
    send_to_gas(archived_streams)


# 使用例
if __name__ == "__main__":
    send_archived_streams_from_excel_channels()
