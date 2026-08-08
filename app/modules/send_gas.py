import requests
import json
from datetime import datetime

def send_to_gas(
    gas_url: str,
    events: list,
    check_duplicate: bool = False
):
    """
    Google Apps Script のカレンダーAPIにイベントデータを送信する共通関数

    Args:
        gas_url (str): GASのWebアプリURL
        events (list): イベントデータのリスト
            例: [
                {
                    "title": "イベント名",
                    "start": "YYYY-MM-DD" または "YYYY-MM-DDTHH:MM:SS+09:00",
                    "end": "YYYY-MM-DD" または "YYYY-MM-DDTHH:MM:SS+09:00",
                    "description": "説明文",
                    "color": "6"
                }
            ]
        check_duplicate (bool): Trueで重複チェックを有効化
    """
    payload = {
        "action": "add",
        "checkDuplicate": check_duplicate,
        "data": events
    }

    try:
        response = requests.post(
            gas_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}

# ===== 使い方例 =====

# # 天気（終日イベント・重複チェックなし）
# weather_event = [{
#     "title": "天気: 晴れ 最高25℃ 最低18℃",
#     "start": "2025-08-14",
#     "end": "2025-08-15",
#     "description": "天気予報詳細...",
#     "color": "6"  # 黄色
# }]

# # YouTube（時間指定イベント・重複チェックあり）
# youtube_event = [{
#     "title": "配信: 新作ゲーム実況",
#     "start": "2025-08-14T20:00:00+09:00",
#     "end": "2025-08-14T22:00:00+09:00",
#     "description": "実況詳細...",
#     "color": "1"  # 青
# }]

# # GASのURL（例）
# GAS_URL = "https://script.google.com/macros/s/xxxxxxxxxxxxxxxx/exec"

# # 送信（天気）
# print(send_to_gas(GAS_URL, weather_event, check_duplicate=False))

# # 送信（YouTube）
# print(send_to_gas(GAS_URL, youtube_event, check_duplicate=True))
