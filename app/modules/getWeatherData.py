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
from pprint import pprint
import os
from datetime import datetime, timedelta, timezone

# JST（日本標準時）
tz = timezone(timedelta(hours=+9), "JST")

# API URLテンプレート
TARGET_URL = "https://api.openweathermap.org/data/2.5/forecast?q={city_name}&units=metric&appid={api_key}"
GAS_URL = os.getenv("GAS_WEATHER_URL")


def get_weather_data(target_date=None):
    """
    指定日の天気データを取得（デフォルトは翌日）
    """
    if target_date is None:
        target_date = datetime.now(tz) + timedelta(days=1)

    target_date_str = target_date.strftime("%Y-%m-%d")

    # 毎回最新データを取得
    request_url = TARGET_URL.format(city_name="Tokyo", api_key=os.getenv("WEATHER_API_KEY"))
    jsondata = requests.get(request_url).json()

    daily_data = []

    for dat in jsondata.get("list", []):
        jst_date = datetime.fromtimestamp(dat["dt"], tz).strftime("%Y-%m-%d")
        if jst_date == target_date_str:
            daily_data.append(dat)

    if daily_data:
        max_temp = max(item["main"]["temp_max"] for item in daily_data)
        min_temp = min(item["main"]["temp_min"] for item in daily_data)
        total_precipitation_prob = sum(item.get("pop", 0) for item in daily_data) / len(daily_data) * 100
        max_pressure = max(item["main"]["pressure"] for item in daily_data)
        min_pressure = min(item["main"]["pressure"] for item in daily_data)
        avg_humidity = sum(item["main"]["humidity"] for item in daily_data) / len(daily_data)

        weather_info = {
            "date": target_date_str,
            "max_temperature": max_temp,
            "min_temperature": min_temp,
            "precipitation_probability": total_precipitation_prob,
            "max_pressure": max_pressure,
            "min_pressure": min_pressure,
            "avg_humidity": avg_humidity
        }
        return weather_info
    else:
        return {"error": f"{target_date_str} のデータは見つかりませんでした。"}


def add_event_to_gas(weather_info):
    headers = {'Content-Type': 'application/json'}

    start_date = weather_info['date']
    end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    insert_data = (
        f"天気: 最高気温 {weather_info['max_temperature']}℃, "
        f"最低気温 {weather_info['min_temperature']}℃, "
        f"降水確率 {weather_info['precipitation_probability']:.1f}%, "
        f"最高気圧 {weather_info['max_pressure']}hPa, "
        f"最低気圧 {weather_info['min_pressure']}hPa, "
        f"平均湿度 {weather_info['avg_humidity']:.1f}%"
    )

    event_data = {
        "action": "add",
        "data": {
            "title": insert_data,
            "start": start_date,
            "end": end_date,
            "description": insert_data,
            "color": "6"
        }
    }
    pprint(event_data)

    try:
        response = requests.post(GAS_URL, headers=headers, json=event_data)
        print("Response status code:", response.status_code)
        print("Response text:", response.text)
        try:
            json_response = response.json()
            print(json.dumps(json_response, ensure_ascii=False, indent=2))
        except json.JSONDecodeError as e:
            print("JSON Decode Error:", e)
            print("Raw response text:", response.text)
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)


def register_tomorrow_weather_to_calendar():
    """
    翌日の天気データを取得してGoogleカレンダーに送信
    """
    weather_info = get_weather_data()
    if "error" not in weather_info:
        add_event_to_gas(weather_info)
    else:
        print("Error fetching weather data:", weather_info["error"])


if __name__ == '__main__':
    register_tomorrow_weather_to_calendar()
