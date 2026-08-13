import csv
import re
from typing import List, Optional, Union, Dict, Any
from datetime import datetime, timedelta, timezone
import os

from myutils.gas_api.use_gas import send_to_gas
from myutils.markdown.headings import (
    extract_lists_from_all_sub_headings,
    extract_lists_from_heading,
    get_heading_task_tree,
)
from myutils.markdown.note_generator import (
    batch_create_dailies_from_file,
    create_weekly_note,
)
from myutils.markdown.utils import parse_vocabulary_line

# タイムゾーン・環境変数の設定
tz = timezone(timedelta(hours=+9), "JST")
GAS_URL = os.getenv("GAS_UTIL_URL")
DAILY_DIR = os.getenv("DAILY_NOTE_DIR")
WEEKLY_DIR = os.getenv("WEEKLY_NOTE_DIR")
DAILY_TASK = os.getenv("DAILY_TASK")

# タグに応じた送信先カレンダーのマップ
TAG_CALENDAR_MAP = {
    "天気": "weather",
    "運動": "Daily Life",
    "アニメ鑑賞": "1 like",
    "映画鑑賞": "1 like",
    "音楽鑑賞": "1 like",
    "ゲーム": "1 like",
    "日記": "Diary",
    "食事": "Daily Life",
    "睡眠": "Daily Life",
    "風呂": "Daily Life"
}

# 基本の色マップ（赤・緑・青・グレーなど）
TAG_COLOR_MAP = {
    # 緑: 生活
    "運動": "RED",
    "散歩": "GREEN",
    "仕事": "GREEN",
    "食事": "GREEN",
    "風呂": "GREEN",
    "睡眠": "GREEN",
    # 青: 趣味
    "アニメ鑑賞": "CYAN",
    "映画鑑賞": "CYAN",
    "音楽鑑賞": "CYAN",
    "ゲーム": "CYAN",
    "読書": "RED",
    # グレー: その他
    "日記": "GRAY",
    "買い物": "GRAY",
}


# ==========================================
# 共通内部ヘルパー関数
# ==========================================

def _parse_lines_to_wordholic(lines: List[str], comment: str) -> List[Dict[str, str]]:
    """箇条書きリストの各行を解析し、Wordholic形式の辞書リストに変換する"""
    rows = []
    for line in lines:
        parsed = parse_vocabulary_line(line)
        if parsed:
            rows.append({
                "FrontText": parsed["word"],
                "BackText": parsed["meaning"],
                "Comment": comment,
                "FrontTextLanguage": "",
                "BackTextLanguage": "",
            })
    return rows


# ==========================================
# Wordholic / CSV 関連関数
# ==========================================

def convert_single_result_to_wordholic(single_result: Dict[str, Any]) -> List[Dict[str, str]]:
    """単一見出しの解析結果をWordholic形式に変換"""
    comment = single_result.get("file_name", "")
    bullets = single_result.get("lists", {}).get("bullets", [])
    return _parse_lines_to_wordholic(bullets, comment)


def convert_all_sub_headings_to_wordholic(all_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """全サブ見出しの解析結果をWordholic形式に変換"""
    all_rows = []
    for res in all_results:
        comment = res.get("heading", "")
        bullets = res.get("lists", {}).get("bullets", [])
        all_rows.extend(_parse_lines_to_wordholic(bullets, comment))
    return all_rows


def export_rows_to_csv(wordholic_rows: List[Dict[str, str]], output_csv_path: str) -> None:
    """Wordholic形式の辞書リストをCSVファイルへ出力"""
    if not wordholic_rows:
        print("⚠️ 出力するデータが見つかりませんでした。")
        return

    fieldnames = ["FrontText", "BackText", "Comment", "FrontTextLanguage", "BackTextLanguage"]

    try:
        with open(output_csv_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(wordholic_rows)
        print(f"✅ CSV出力完了: {output_csv_path}")
    except Exception as e:
        print(f"❌ CSV出力エラー: {e}")


def export_english_vocabulary() -> None:
    """英単語のMarkdownからWordholic CSVを出力"""
    file_path = os.getenv("PATH_ENG")
    target_heading = os.getenv("TARGET_HEAD_ENG")
    if not file_path or not target_heading:
        print("❌ エラー: PATH_ENG または TARGET_HEAD_ENG が設定されていません。")
        return

    all_results = extract_lists_from_all_sub_headings(file_path, target_heading)
    all_rows = convert_all_sub_headings_to_wordholic(all_results)
    export_rows_to_csv(all_rows, "output_all.csv")


def export_single_vocabulary() -> None:
    """単一語彙のMarkdownからWordholic CSVを出力"""
    file_path = os.getenv("PATH_VOCAB")
    target_heading = os.getenv("TARGET_HEAD_VOCAB")
    if not file_path or not target_heading:
        print("❌ エラー: PATH_VOCAB または TARGET_HEAD_VOCAB が設定されていません。")
        return

    single_result = extract_lists_from_heading(file_path, target_heading)
    single_rows = convert_single_result_to_wordholic(single_result)
    export_rows_to_csv(single_rows, "output_single.csv")


# ==========================================
# ノート自動生成関数
# ==========================================

def create_dailynote() -> None:
    """デイリーノートを生成（向こう7日間分）"""
    target_path = os.getenv("DAILY_NOTE_DIR")
    template_path = os.getenv("DAILY_NOTE_TEMPLATE")
    start_date = datetime.now()
    batch_create_dailies_from_file(target_path, start_date, 7, template_path)


def create_next_weekly_note() -> None:
    """翌週分のウィークリーノートを生成"""
    output_dir = os.getenv("WEEKLY_NOTE_DIR")
    template_path = os.getenv("WEEKLY_NOTE_TEMPLATE")
    plan_dir = os.getenv("PLAN_NOTE_DIR")

    next_week_date = datetime.now() + timedelta(days=7)

    create_weekly_note(
        output_dir=output_dir,
        target_date=next_week_date,
        template_path=template_path,
        plan_dir=plan_dir,
        start_of_week="monday",
    )


# ==========================================
# Google Calendar / GAS 連携関数
# ==========================================

def get_focus_tags_from_weekly_note(
    weekly_dir: str, target_date: datetime, sunday_first: bool = False
) -> List[str]:
    """指定された日付の属する週の Weekly Note (例: 2026-W34.md) から「頑張りたいこと」を取得"""
    date_for_calc = target_date
    if sunday_first and target_date.weekday() == 6:
        date_for_calc = target_date + timedelta(days=1)

    year, week_num, _ = date_for_calc.isocalendar()
    filename = f"{year}-W{week_num:02d}.md"
    file_path = os.path.join(weekly_dir, filename)

    if not os.path.exists(file_path):
        print(f"[INFO] Weekly Note ({filename}) が見つからないため、目標タグなしで処理します。")
        return []

    focus_tags = []
    in_target_heading = False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()

                if re.match(r"^#+\s+頑張りたいことを書き出す", line_str):
                    in_target_heading = True
                    continue
                elif in_target_heading and line_str.startswith("#"):
                    break

                if in_target_heading and (line_str.startswith("- ") or line_str.startswith("* ")):
                    tag = re.sub(r"^[-*]\s+(\[[\sxX]\]\s*)?", "", line_str).strip()
                    if tag:
                        focus_tags.append(tag)
    except Exception as e:
        print(f"⚠️ Weekly Note 読み込み中にエラーが発生しました: {e}")

    print(f"[INFO] 今週の目標タグ ({filename}): {focus_tags}")
    return focus_tags


def register_tasks_from_markdown_to_calendar(
    file_path: Union[str, List[str]],
    target_heading: str,
    weekly_dir: str,
    start_time: Optional[Union[str, datetime]] = None,
    default_calendar_key: str = "Daily Life",
    sunday_first: bool = False,
) -> None:
    """Markdown（複数ファイル対応）からタスクを読み込み、GAS経由でGoogleカレンダーに登録する"""
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    elif start_time is None:
        start_time = datetime.now(tz)

    focus_tags = get_focus_tags_from_weekly_note(weekly_dir, start_time, sunday_first=sunday_first)

    # --- 各ファイルから個別でタスクツリーを取得して結合 ---
    file_paths = [file_path] if isinstance(file_path, str) else file_path
    combined_task_tree = []

    for path in file_paths:
        if path and os.path.exists(path):
            tasks = get_heading_task_tree(path, target_heading)
            if tasks:
                print(f"[DEBUG] {os.path.basename(path)} から {len(tasks)} 件のタスクノードを取得しました")
                combined_task_tree.extend(tasks)
            else:
                print(f"[DEBUG] {os.path.basename(path)} には '{target_heading}' のタスクがありませんでした")

    if not combined_task_tree:
        print(f"❌ タスクが見つかりませんでした: {target_heading}")
        return

    events_by_calendar: Dict[str, List[Dict[str, Any]]] = {}
    current_time = start_time

    # 統合した combined_task_tree を順に処理
    for node in combined_task_tree:
        if "tag" in node and "minutes" in node:
            tag = node["tag"]
            
            # --- 子タスクのテキスト抽出 ---
            raw_children = node.get("children", [])
            children_texts = []
            for c in raw_children:
                if isinstance(c, dict):
                    children_texts.append(c.get("text", ""))
                elif isinstance(c, str):
                    children_texts.append(c)

            children_texts = [t.strip() for t in children_texts if t.strip()]

            children_str = ", ".join(children_texts)
            title = f"{tag}: {children_str}" if children_str else tag
            description = "\n".join(f"- {t}" for t in children_texts)

            # --- 時間指定の割り込み処理 ---
            node_start_time = node.get("start_time")
            if node_start_time:
                try:
                    hour_str, min_str = node_start_time.split(":")
                    current_time = current_time.replace(
                        hour=int(hour_str),
                        minute=int(min_str),
                        second=0,
                        microsecond=0
                    )
                except ValueError:
                    pass

            duration = timedelta(minutes=node["minutes"])
            end_time = current_time + duration

            # 色の決定
            if tag in focus_tags:
                event_color = "RED"
            else:
                event_color = TAG_COLOR_MAP.get(tag)

            target_cal_key = TAG_CALENDAR_MAP.get(tag, default_calendar_key)

            event_payload = {
                "title": title,
                "start": current_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": description,
                "color": event_color,
            }

            events_by_calendar.setdefault(target_cal_key, []).append(event_payload)
            current_time = end_time

    print("\n🚀 GASへカレンダーイベントを送信中...")
    for cal_key, events in events_by_calendar.items():
        payload = {
            "calendarKey": cal_key,
            "data": events,
        }
        try:
            response = send_to_gas(
                data=payload,
                gas_url=GAS_URL,
                action_name=f"Calendar: {cal_key}",
            )

            if response and response.status_code == 200:
                res_json = response.json()
                if res_json.get("success"):
                    print(f"✅ 【{cal_key}】 ({len(events)} 件) Googleカレンダーへの登録成功！")
                else:
                    print(f"⚠️ 【{cal_key}】 GAS側エラー: {res_json.get('error')}")
            else:
                status_code = response.status_code if response else "No Response"
                print(f"❌ 【{cal_key}】 HTTP通信エラー: {status_code}")
        except Exception as e:
            print(f"❌ 【{cal_key}】 送信例外発生: {e}")

    print("カレンダー登録処理が完了しました")
    print("=" * 60)

def register_tasks_by_date(
    target_date: str,
    start_hour_min: str = "15:00",
    target_heading: str = "Tasks",
    sunday_first: bool = False,
) -> None:
    """日付指定でMarkdownからタスクを読み込み、GASへ登録するラッパー関数"""
    if not DAILY_DIR:
        print("❌ エラー: 環境変数 DAILY_NOTE_DIR が設定されていません。")
        return

    file_path = os.path.join(DAILY_DIR, f"{target_date}.md")
    start_time_str = f"{target_date} {start_hour_min}"

    print(f"📅 【対象日】: {target_date}")
    print(f"📄 【ファイル】: {file_path}")
    if DAILY_TASK and os.path.exists(DAILY_TASK):
        print(f"🔄 【共通タスク】: {DAILY_TASK}")
    print(f"⏰ 【開始時刻】: {start_time_str}\n")

    # 読み込む対象ファイルリストを作成
    target_files = []

    # 1. 個別ノート（例: 2026-08-15.md）を先にリストに追加
    if os.path.exists(file_path):
        target_files.append(file_path)
    else:
        print(f"⚠️ 指定日のノートが存在しないため、DAILY_TASK のみを処理対象とします: {file_path}")

    # 2. DAILY_TASK（ルーティン）を後にリストに追加
    if DAILY_TASK and os.path.exists(DAILY_TASK):
        target_files.append(DAILY_TASK)

    if not target_files:
        print("❌ 処理対象のファイル（DAILY_TASK / 個別ノート）が存在しません。")
        return

    register_tasks_from_markdown_to_calendar(
        file_path=target_files,  # 個別ノート -> DAILY_TASK の順で渡される
        target_heading=target_heading,
        weekly_dir=WEEKLY_DIR or DAILY_DIR,
        start_time=start_time_str,
        sunday_first=sunday_first,
    )


def test_md() -> None:
    """動作確認用テスト関数"""
    print("================test_md===============")
    today_str = datetime.now().strftime("%Y-%m-%d")
    register_tasks_by_date(
        target_date=today_str,
        start_hour_min="15:00",
        sunday_first=False,
    )
