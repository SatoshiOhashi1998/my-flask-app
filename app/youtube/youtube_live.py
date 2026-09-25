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
- `os`, `time`, `datetime`, `timedelta`, `pytz`, `isodate`, `pandas`

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
    - video_id: 動画ID（必須）
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
2. `get_archived_live_streams_by_query`、`get_archived_live_streams_by_channelid`または
   `get_archived_live_stream_by_videoid`を使用してアーカイブされたライブストリーム情報を取得します。
3. `send_to_gas`関数を呼び出し、取得したデータをGASに送信します。
"""

import os
import time
from datetime import datetime, timedelta

import isodate
import pandas as pd
import pytz

from app.youtube.youtube_api import create_youtube_api

from myutils.gas_api.use_gas import send_to_gas


GAS_URL = os.getenv("GAS_UTIL_URL")


def get_archived_live_streams_by_channelid(
    channel_ids,
    published_after=None,
    published_before=None,
):
    yt_api = create_youtube_api()

    archived_streams = []

    if published_after is None:
        published_after = datetime.utcnow() - timedelta(days=1)

    if published_before is None:
        published_before = datetime.utcnow()

    for channel_id in channel_ids:
        next_page_token = None

        while True:
            response = yt_api.search_videos(
                channel_id=channel_id,
                published_after=published_after,
                published_before=published_before,
                event_type="completed",
                max_results=10,
                order="date",
                page_token=next_page_token,
            )

            items = response.get("items", [])

            if not items:
                break

            for event in items:
                video_id = event["id"]["videoId"]
                channel_title = event["snippet"]["channelTitle"]

                # 動画の詳細情報を取得
                video_info = yt_api.get_video_details(
                    video_id,
                    part="contentDetails",
                )

                if video_info is None:
                    continue

                duration_iso = video_info["contentDetails"].get(
                    "duration",
                    "PT0S",
                )

                published_at = event["snippet"]["publishedAt"]

                utc_time = datetime.fromisoformat(
                    published_at[:-1]
                )

                end_time = utc_time.replace(tzinfo=pytz.utc)

                duration_timedelta = isodate.parse_duration(
                    duration_iso
                )

                start_time = end_time - duration_timedelta

                # JSTに変換
                jst_tz = pytz.timezone("Asia/Tokyo")

                jst_start_time = start_time.astimezone(jst_tz)
                jst_end_time = end_time.astimezone(jst_tz)

                stream_url = (
                    f"https://www.youtube.com/watch?v={video_id}"
                )

                archived_streams.append({
                    "title": "配信: " + event["snippet"]["title"],
                    "start": jst_start_time.isoformat(),
                    "end": jst_end_time.isoformat(),
                    "description": (
                        f"配信元: {channel_title}\n"
                        f"リンク: {stream_url}"
                    ),
                    "allDay": False,
                    "color": "BLUE",
                })

            next_page_token = response.get("nextPageToken")

            if not next_page_token:
                break

            time.sleep(1)

        time.sleep(1)

    send_data = {
        "action": "youtube",
        "data": archived_streams,
    }

    return send_data


def get_archived_live_streams_by_query(
    query,
    published_after=None,
    published_before=None,
):
    yt_api = create_youtube_api()

    archived_streams = []

    if published_after is None:
        published_after = datetime.utcnow() - timedelta(days=7)

    if published_before is None:
        published_before = datetime.utcnow()

    next_page_token = None

    while True:
        response = yt_api.search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            event_type="completed",
            max_results=50,
            order="date",
            page_token=next_page_token,
        )

        items = response.get("items", [])

        if not items:
            break

        for event in items:
            video_id = event["id"]["videoId"]
            channel_title = event["snippet"]["channelTitle"]

            video_info = yt_api.get_video_details(
                video_id,
                part="contentDetails",
            )

            if video_info is None:
                continue

            duration_iso = video_info["contentDetails"].get(
                "duration",
                "PT0S",
            )

            published_at = event["snippet"]["publishedAt"]

            utc_time = datetime.fromisoformat(
                published_at[:-1]
            )

            end_time = utc_time.replace(tzinfo=pytz.utc)

            duration_timedelta = isodate.parse_duration(
                duration_iso
            )

            start_time = end_time - duration_timedelta

            jst_tz = pytz.timezone("Asia/Tokyo")

            jst_start_time = start_time.astimezone(jst_tz)
            jst_end_time = end_time.astimezone(jst_tz)

            stream_url = (
                f"https://www.youtube.com/watch?v={video_id}"
            )

            archived_streams.append({
                "title": "配信: " + event["snippet"]["title"],
                "start": jst_start_time.isoformat(),
                "end": jst_end_time.isoformat(),
                "description": (
                    f"配信元: {channel_title}\n"
                    f"リンク: {stream_url}"
                ),
                "allDay": False,
                "color": "BLUE",
            })

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

        time.sleep(1)

    send_data = {
        "action": "youtube",
        "data": archived_streams,
    }

    return send_data


def get_archived_live_stream_by_videoid(video_id):
    yt_api = create_youtube_api()

    archived_streams = []

    video_info = yt_api.get_video_details(
        video_id,
        part="snippet,contentDetails",
    )

    if video_info is None:
        return {
            "error": "Video not found or is not an archived live stream"
        }

    duration = video_info["contentDetails"].get(
        "duration",
        "PT0S",
    )

    published_at = video_info["snippet"]["publishedAt"]
    title = video_info["snippet"]["title"]
    channel_title = video_info["snippet"]["channelTitle"]

    end_time = datetime.fromisoformat(
        published_at[:-1]
    ).replace(tzinfo=pytz.utc)

    duration_timedelta = isodate.parse_duration(duration)

    start_time = end_time - duration_timedelta

    jst_tz = pytz.timezone("Asia/Tokyo")

    jst_start_time = start_time.astimezone(jst_tz)
    jst_end_time = end_time.astimezone(jst_tz)

    stream_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    archived_streams.append({
        "title": "配信: " + title,
        "start": jst_start_time.isoformat(),
        "end": jst_end_time.isoformat(),
        "description": (
            f"配信元: {channel_title}\n"
            f"リンク: {stream_url}"
        ),
        "allDay": False,
        "color": "BLUE",
    })

    send_data = {
        "action": "youtube",
        "data": archived_streams,
    }

    return send_data


def get_archived_live_streams_by_playlistid(playlist_id):
    yt_api = create_youtube_api()

    archived_streams = []

    next_page_token = None

    while True:
        response = yt_api.get_playlist_items(
            playlist_id=playlist_id,
            max_results=50,
            page_token=next_page_token,
        )

        items = response.get("items", [])

        if not items:
            break

        video_ids = [
            item["snippet"]["resourceId"]["videoId"]
            for item in items
        ]

        for video_id in video_ids:
            video_info = yt_api.get_video_details(
                video_id,
                part="snippet,contentDetails",
            )

            if video_info is None:
                continue

            snippet = video_info["snippet"]
            content_details = video_info["contentDetails"]

            title = "配信: " + snippet["title"]
            published_at = snippet["publishedAt"]
            channel_title = snippet["channelTitle"]

            duration = content_details.get(
                "duration",
                "PT0S",
            )

            utc_time = datetime.fromisoformat(
                published_at[:-1]
            )

            end_time = utc_time.replace(tzinfo=pytz.utc)

            duration_timedelta = isodate.parse_duration(
                duration
            )

            start_time = end_time - duration_timedelta

            jst_tz = pytz.timezone("Asia/Tokyo")

            jst_start_time = start_time.astimezone(jst_tz)
            jst_end_time = end_time.astimezone(jst_tz)

            stream_url = (
                f"https://www.youtube.com/watch?v={video_id}"
            )

            archived_streams.append({
                "title": title,
                "start": jst_start_time.isoformat(),
                "end": jst_end_time.isoformat(),
                "description": (
                    f"配信元: {channel_title}\n"
                    f"リンク: {stream_url}"
                ),
                "allDay": False,
                "color": "BLUE",
            })

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

        time.sleep(1)

    send_data = {
        "action": "youtube",
        "data": archived_streams,
    }

    return send_data


def get_channel_ids_from_excel():
    """
    チャンネルIDをまとめているExcelファイルからデータを取得。
    チャンネルIDのリストを返す。
    """
    csv_path = os.getenv("CHANNEL_CSV_PATH")
    sheet_name = "データ"

    # Excelファイルを読み込み
    excel_data = pd.read_excel(
        csv_path,
        sheet_name=sheet_name,
    )

    print("列名:", excel_data.columns.tolist())

    # favorite == 1 のチャンネルIDを取得
    channel_ids = excel_data[
        excel_data["favorite"] == 1
    ]["channelId"].tolist()

    return channel_ids


def send_archived_streams_from_excel_channels():
    channel_ids = get_channel_ids_from_excel()

    archived_streams = get_archived_live_streams_by_channelid(
        channel_ids
    )

    send_to_gas(
        archived_streams,
        GAS_URL,
    )
