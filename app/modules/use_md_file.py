import csv
from datetime import datetime, timedelta, timezone
import os
import re
from myutils.markdown.headings import (
    extract_lists_from_all_sub_headings,
    extract_lists_from_heading,
    find_headings_by_tag_in_directory,
    get_content_by_heading,
    get_heading_task_tree,
)
from myutils.markdown.lists import (
    extract_nested_lists_from_content,
)
from myutils.markdown.note_generator import (
    batch_create_dailies_from_file,
    create_weekly_note,
)
from myutils.markdown.utils import parse_vocabulary_line, parse_tag_time_line

from myutils.gas_api.use_gas import send_to_gas

tz = timezone(timedelta(hours=+9), "JST")
GAS_URL = os.getenv("GAS_UTIL_URL")
DAILY_DIR = os.getenv("DAILY_NOTE_DIR")
WEEKLY_DIR = os.getenv("WEEKLY_NOTE_DIR")

# タグに応じた送信先カレンダーのマップ
TAG_CALENDAR_MAP = {
    "天気": "weather",
    "運動": "Daily Life",
    "アニメ鑑賞": "1 like",
    "映画鑑賞": "1 like",
    "音楽鑑賞": "1 like",
    "ゲーム": "1 like",
    "日記": "Diary",
}

# 基本の色マップ（赤・緑・青・グレーなど）
TAG_COLOR_MAP = {
    # 緑: 生活
    "運動": "RED",
    "散歩": "GREEN",
    "仕事": "GREEN",
    "食事": "GREEN",
    "風呂": "GREEN",
    # 青: 趣味
    "アニメ鑑賞": "BLUE",
    "映画鑑賞": "BLUE",
    "音楽鑑賞": "BLUE",
    "ゲーム": "BLUE",
    "読書": "RED",
    # グレー: その他
    "日記": "GRAY",
    "買い物": "GRAY",
}

def convert_single_result_to_wordholic(single_result):
    comment = single_result['file_name']
    wordholic_rows = []
    
    for line in single_result['lists'].get('bullets', []):
        parsed = parse_vocabulary_line(line)
        if parsed:
            wordholic_rows.append({
                "FrontText": parsed["word"],
                "BackText": parsed["meaning"],
                "Comment": comment,
                "FrontTextLanguage": "",
                "BackTextLanguage": ""
            })
            
    return wordholic_rows

def convert_all_sub_headings_to_wordholic(all_results):
    all_wordholic_rows = []
    
    for res in all_results:
        comment = res['heading']
        for line in res['lists'].get('bullets', []):
            parsed = parse_vocabulary_line(line)
            if parsed:
                all_wordholic_rows.append({
                    "FrontText": parsed["word"],
                    "BackText": parsed["meaning"],
                    "Comment": comment,
                    "FrontTextLanguage": "",
                    "BackTextLanguage": ""
                })
                
    return all_wordholic_rows

def export_rows_to_csv(wordholic_rows, output_csv_path):
    if not wordholic_rows:
        print("出力するデータが見つかりませんでした。")
        return

    fieldnames = ["FrontText", "BackText", "Comment", "FrontTextLanguage", "BackTextLanguage"]
    
    try:
        with open(output_csv_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(wordholic_rows)
            
        print(f"CSV出力完了: {output_csv_path}")
    except Exception as e:
        print(f"CSV出力エラー: {e}")

def create_dailynote():
    target_path = os.getenv('DAILY_NOTE_DIR')
    template_path = os.getenv('DAILY_NOTE_TEMPLATE')
    start_date = datetime.now()
    batch_create_dailies_from_file(target_path, start_date, 7, template_path)

def create_next_weekly_note():
    output_dir = os.getenv('WEEKLY_NOTE_DIR')
    template_path = os.getenv('WEEKLY_NOTE_TEMPLATE')
    plan_dir = os.getenv('PLAN_NOTE_DIR')
    
    today = datetime.now()
    next_week_date = today + timedelta(days=7)
    
    create_weekly_note(
        output_dir=output_dir,
        target_date=next_week_date,
        template_path=template_path,
        plan_dir=plan_dir,
        start_of_week="monday"
    )

def export_english_vocabulary():
    file_path = os.getenv("PATH_ENG")
    target_heading = os.getenv("TARGET_HEAD_ENG")
    all_results = extract_lists_from_all_sub_headings(file_path, target_heading)
    all_rows = convert_all_sub_headings_to_wordholic(all_results)
    export_rows_to_csv(all_rows, "output_all.csv")

def export_single_vocabulary():
    file_path = os.getenv("PATH_VOCAB")
    target_heading = os.getenv("TARGET_HEAD_VOCAB")
    single_result = extract_lists_from_heading(file_path, target_heading)
    single_rows = convert_single_result_to_wordholic(single_result)
    export_rows_to_csv(single_rows, "output_single.csv")

def test_md():
    print("================test_md===============")
    # パスと引数を指定して実行
    register_tasks_by_date(
        target_date="2026-08-13",
        start_hour_min="15:00",
        sunday_first=False,
    )


def register_tasks_from_markdown_to_calendar(
    file_path: str,
    target_heading: str,
    weekly_dir: str,
    start_time: datetime = None,
    default_calendar_key: str = "Daily Life",
    sunday_first: bool = False,
):
    """Markdownからタスクを読み込み、GAS経由でGoogleカレンダーに登録する"""

    # 時刻の設定
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M").replace(
            tzinfo=tz
        )
    elif start_time is None:
        start_time = datetime.now(tz)

    # 1. Weekly Note から今週の目標タグを取得
    focus_tags = get_focus_tags_from_weekly_note(
        weekly_dir, start_time, sunday_first=sunday_first
    )

    # 2. タスクツリーの取得
    task_tree = get_heading_task_tree(file_path, target_heading)
    if not task_tree:
        print(f"❌ タスクが見つかりませんでした: {target_heading}")
        return

    events_by_calendar = {}
    current_time = start_time

    for node in task_tree:
        if "tag" in node and "minutes" in node:
            tag = node["tag"]

            children_texts = [c["text"] for c in node.get("children", [])]
            children_str = ", ".join(children_texts)

            title = f"{tag}: {children_str}" if children_str else tag
            description = "\n".join(f"- {t}" for t in children_texts)

            duration = timedelta(minutes=node["minutes"])
            end_time = current_time + duration

            # --- 色の決定 ---
            is_focus = tag in focus_tags
            if is_focus:
                event_color = "RED"
            elif tag in TAG_COLOR_MAP:
                event_color = TAG_COLOR_MAP[tag]
            else:
                event_color = None

            # --- 送信先カレンダーの決定 ---
            target_cal_key = TAG_CALENDAR_MAP.get(tag, default_calendar_key)

            # ペイロード作成
            event_payload = {
                "title": title,
                "start": current_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": description,
                "color": event_color,
            }

            if target_cal_key not in events_by_calendar:
                events_by_calendar[target_cal_key] = []
            events_by_calendar[target_cal_key].append(event_payload)

            current_time = end_time

    print("\n🚀 GASへカレンダーイベントを送信中...")
    for cal_key, events in events_by_calendar.items():
        # GASの仕様に合わせてキー名を修正
        payload = {
            "calendarKey": cal_key,  # calendar_key -> calendarKey
            "data": events,          # events -> data
        }
        try:
            response = send_to_gas(
                data=payload,
                gas_url=GAS_URL,
                action_name=f"Calendar: {cal_key}"
            )
            
            if response and response.status_code == 200:
                res_json = response.json()
                if res_json.get("success"):
                    print(f"✅ 【{cal_key}】 ({len(events)} 件) Googleカレンダーへの登録成功！")
                else:
                    print(f"⚠️ 【{cal_key}】 GAS側エラー: {res_json.get('error')}")
            else:
                print(f"❌ 【{cal_key}】 HTTP通信エラー: {response.status_code if response else 'No Response'}")
        except Exception as e:
            print(f"❌ 【{cal_key}】 送信例外発生: {e}")

    print("  カレンダー登録処理が完了しました")
    print("=" * 60)

def get_focus_tags_from_weekly_note(
    weekly_dir: str, target_date: datetime, sunday_first: bool = False
) -> list[str]:
    """指定された日付の属する週の Weekly Note (例: 2026-W34.md) から「頑張りたいこと」のリストを取得する

    Args:
        weekly_dir (str): Weekly Noteが保存されているディレクトリのパス
        target_date (datetime): 対象の日付
        sunday_first (bool): Trueなら日曜始まり、Falseなら月曜始まり (デフォルト: False)
    """
    # 日曜始まりの場合の調整
    # 日曜日(weekday() == 6)の場合、1日足して月曜日扱いにすることで、次の週番号(ISO)にシフトさせる
    date_for_calc = target_date
    if sunday_first and target_date.weekday() == 6:
        date_for_calc = target_date + timedelta(days=1)

    # 週番号の計算 (年, 週番号, 曜日)
    year, week_num, _ = date_for_calc.isocalendar()
    filename = f"{year}-W{week_num:02d}.md"
    file_path = os.path.join(weekly_dir, filename)

    if not os.path.exists(file_path):
        print(
            f"[INFO] Weekly Note ({filename}) が見つからないため、目標タグなしで処理します。"
        )
        return []

    focus_tags = []
    in_target_heading = False

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()

            # 見出しの判定 (# 頑張りたいことを書き出す)
            if re.match(r"^#+\s+頑張りたいことを書き出す", line_str):
                in_target_heading = True
                continue
            elif in_target_heading and line_str.startswith("#"):
                # 別の見出しが始まったら終了
                break

            # 見出し配下の箇条書き (- や * のリスト) を抽出
            if in_target_heading and (
                line_str.startswith("- ") or line_str.startswith("* ")
            ):
                tag = re.sub(r"^[-*]\s+(\[[\sxX]\]\s*)?", "", line_str).strip()
                if tag:
                    focus_tags.append(tag)

    print(f"[INFO] 今週の目標タグ ({filename}): {focus_tags}")
    return focus_tags

def register_tasks_by_date(
    target_date: str,
    start_hour_min: str = "15:00",
    target_heading: str = "Tasks",
    sunday_first: bool = False,
):
    """日付指定でMarkdownからタスクを読み込み、GASへ登録するラッパー関数

    Args:
        target_date (str): 処理対象日 ("YYYY-MM-DD" 形式)
        start_hour_min (str): 開始時刻 ("HH:MM" 形式)
        target_heading (str): 対象の見出し
        sunday_first (bool): 週の始まりが日曜日かどうか
    """
    if not DAILY_DIR:
        print("❌ エラー: 環境変数 OBSIDIAN_DAILY_DIR が設定されていません。")
        return

    # 日付からファイルパスを動的に組み立て
    file_path = os.path.join(DAILY_DIR, f"{target_date}.md")

    # 日付と時刻を結合して start_time を作成
    start_time_str = f"{target_date} {start_hour_min}"

    print(f"📅 【対象日】: {target_date}")
    print(f"📄 【ファイル】: {file_path}")
    print(f"⏰ 【開始時刻】: {start_time_str}\n")

    # ファイルの存在チェック
    if not os.path.exists(file_path):
        print(f"❌ ファイルが存在しません: {file_path}")
        return

    # 既存のメイン関数を呼び出し
    register_tasks_from_markdown_to_calendar(
        file_path=file_path,
        target_heading=target_heading,
        weekly_dir=WEEKLY_DIR or DAILY_DIR,
        start_time=start_time_str,
        sunday_first=sunday_first,
    )
