"""
天気情報取得およびGoogleカレンダーへの送信モジュール

このモジュールは、OpenWeatherMap APIを使用して特定の都市（デフォルトは東京）の天気予報を取得し、Google Apps Script（GAS）を介してGoogleカレンダーに天気情報を追加します。
アプリケーションは、毎日23時に起動するように設計されています。

使用方法:
1. 環境変数にOpenWeatherMapのAPIキー（WEATHER_API_KEY）とGASのURL（GAS_WEATHER_URL）を設定します。
2. `main()` 関数を実行して天気データを取得し、Googleカレンダーにイベントを追加します。

依存関係:
- requests: HTTPリクエストを送信するためのライブラリ。
- json: JSONデータの処理に使用される標準ライブラリ。
- pprint: 整形されたデータの出力に使用される標準ライブラリ。
- os: 環境変数へのアクセスに使用される標準ライブラリ。
- datetime: 日付と時刻の操作に使用される標準ライブラリ。

設定内容:
- デフォルトでは東京の天気データを取得しますが、他の都市に変更することも可能です。
- 天気情報は翌日の最高気温、最低気温、降水確率を含みます。
- Googleカレンダーに追加されるイベントは終日イベントとして設定されます。

"""
import requests
import json
import os
from datetime import datetime, timedelta, timezone
from myutils.gas_api.use_gas import send_to_gas

# JST（日本標準時）
tz = timezone(timedelta(hours=+9), "JST")

# API URLテンプレート
TARGET_URL = "https://api.openweathermap.org/data/2.5/forecast?q={city_name}&units=metric&appid={api_key}"
GAS_URL = os.getenv("GAS_UTIL_URL")


def get_weather_data(target_date=None, city_name="Tokyo"):
    """
    指定日の天気データを取得し、Googleカレンダー用のevent_dataを作成
    （デフォルトは翌日の東京）
    """
    if target_date is None:
        target_date = datetime.now(tz) + timedelta(days=1)

    target_date_str = target_date.strftime("%Y-%m-%d")

    # 最新データ取得
    request_url = TARGET_URL.format(city_name=city_name, api_key=os.getenv("WEATHER_API_KEY"))
    jsondata = requests.get(request_url).json()

    daily_data = [
        dat for dat in jsondata.get("list", [])
        if datetime.fromtimestamp(dat["dt"], tz).strftime("%Y-%m-%d") == target_date_str
    ]

    if not daily_data:
        return {"error": f"{target_date_str} のデータは見つかりませんでした。"}

    # 必要な気象データを集計
    max_temp = max(item["main"]["temp_max"] for item in daily_data)
    min_temp = min(item["main"]["temp_min"] for item in daily_data)
    total_precipitation_prob = sum(item.get("pop", 0) for item in daily_data) / len(daily_data) * 100
    max_pressure = max(item["main"]["pressure"] for item in daily_data)
    min_pressure = min(item["main"]["pressure"] for item in daily_data)
    avg_humidity = sum(item["main"]["humidity"] for item in daily_data) / len(daily_data)

    insert_data = (
        f"天気: 最高気温 {max_temp}℃, "
        f"最低気温 {min_temp}℃, "
        f"降水確率 {total_precipitation_prob:.1f}%, "
        f"最高気圧 {max_pressure}hPa, "
        f"最低気圧 {min_pressure}hPa, "
        f"平均湿度 {avg_humidity:.1f}%"
    )

    end_date = (datetime.strptime(target_date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    event_data = {
        "action": "weather",
        "data": [{
            "title": insert_data,
            "start": target_date_str,
            "end": end_date,
            "description": insert_data,
            "allDay": True,
            "color": "YELLOW"
        }]
    }

    return event_data


def register_tomorrow_weather_to_calendar():
    """
    翌日の天気データを取得してGoogleカレンダーに送信
    """
    event_data = get_weather_data()
    if "error" not in event_data:
        send_to_gas(event_data, GAS_URL)
    else:
        print("Error:", event_data["error"])


if __name__ == '__main__':
    register_tomorrow_weather_to_calendar()
