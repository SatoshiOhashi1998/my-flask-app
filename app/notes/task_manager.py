import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from myutils.markdown.note_processor import Note, NoteParser
from myutils.gas_api.use_gas import send_to_gas


tz = timezone(timedelta(hours=9))

GAS_URL = os.getenv("GAS_UTIL_URL")

DAILY_DIR = os.getenv("DAILY_NOTE_DIR")
WEEKLY_DIR = os.getenv("WEEKLY_NOTE_DIR")
DAILY_TASK = os.getenv("DAILY_TASK")


# タグに応じた送信先カレンダーのマップ
TAG_CALENDAR_MAP = {
    # Daily Life
    "運動": "Daily Life",
    "食事": "Daily Life",
    "睡眠": "Daily Life",
    "風呂": "Daily Life",
    # 1 like
    "アニメ鑑賞": "1 like",
    "映画鑑賞": "1 like",
    "音楽鑑賞": "1 like",
    "ゲーム": "1 like",
    "動画": "1 like",
    "配信": "1 like",
    "配信視聴": "1 like",
    "雑談配信": "1 like",
    "傾聴雑談": "1 like",
    "倍速雑談": "1 like",
    "将棋": "1 like",
    # その他
    "天気": "Daily Life",
    "勉強": "Diary",
    "日記": "Diary",
}

# 基本の色マップ（赤・緑・青・グレーなど）
TAG_COLOR_MAP = {
    # 緑: 生活
    "仕事": "GREEN",
    "運動": "RED",
    "散歩": "GREEN",
    "食事": "GREEN",
    "睡眠": "GREEN",
    "風呂": "GREEN",
    # 青: 趣味
    "アニメ鑑賞": "CYAN",
    "映画鑑賞": "CYAN",
    "音楽鑑賞": "CYAN",
    "ゲーム": "CYAN",
    "動画": "CYAN",
    "配信": "CYAN",
    "配信視聴": "CYAN",
    "雑談配信": "CYAN",
    "傾聴雑談": "RED",
    "倍速雑談": "RED",
    "勉強": "RED",
    "読書": "RED",
    "将棋": "CYAN",
    # グレー: その他
    "日記": "GRAY",
    "買い物": "GRAY",
    "天気": "GREEN",
}


def get_focus_tags_from_weekly_note(
    weekly_dir: str, target_date: datetime, sunday_first: bool = False
) -> List[str]:
    """指定された日付の属する週のWeekly Noteから「頑張りたいこと」を取得"""
    date_for_calc = target_date
    if sunday_first and target_date.weekday() == 6:
        date_for_calc = target_date + timedelta(days=1)

    year, week_num, _ = date_for_calc.isocalendar()
    filename = f"{year}-W{week_num:02d}.md"
    file_path = os.path.join(weekly_dir, filename)

    if not os.path.exists(file_path):
        print(
            f"[INFO] Weekly Note ({filename}) が見つからないため、"
            "目標タグなしで処理します。"
        )
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

                if in_target_heading and (
                    line_str.startswith("- ") or line_str.startswith("* ")
                ):
                    tag = re.sub(
                        r"^[-*]\s+(\[[\sxX]\]\s*)?",
                        "",
                        line_str,
                    ).strip()

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
    """Markdownからタスクを読み込み、GAS経由でGoogleカレンダーに登録する"""

    if isinstance(start_time, str):
        start_time = datetime.strptime(
            start_time, "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz)
    elif start_time is None:
        start_time = datetime.now(tz)

    focus_tags = get_focus_tags_from_weekly_note(
        weekly_dir,
        start_time,
        sunday_first=sunday_first,
    )

    # --- 各ファイルから個別でタスクツリーを取得して結合 ---
    file_paths = [file_path] if isinstance(file_path, str) else file_path
    combined_task_tree = []

    for path in file_paths:
        if path and os.path.exists(path):
            tasks = NoteParser(
                Note(path)
            ).get_heading_task_tree(target_heading)

            if tasks:
                print(
                    f"[DEBUG] {os.path.basename(path)} から "
                    f"{len(tasks)} 件のタスクノードを取得しました"
                )
                combined_task_tree.extend(tasks)
            else:
                print(
                    f"[DEBUG] {os.path.basename(path)} には "
                    f"'{target_heading}' のタスクがありませんでした"
                )

    if not combined_task_tree:
        print(f"❌ タスクが見つかりませんでした: {target_heading}")
        return

    events_by_calendar: Dict[str, List[Dict[str, Any]]] = {}

    # 基準となる日付を固定（日付跨ぎによる時間ズレを防止）
    base_date = start_time.date()
    current_time = start_time

    # 統合したcombined_task_treeを順に処理
    for node in combined_task_tree:
        if "tag" in node and "minutes" in node:
            tag = node["tag"]

        # --- 子タスクとメモの抽出 ---
        raw_children = node.get("children", []) or []

        def clean_item_text(item: dict) -> str:
            """本文からObsidian内部リンクを除去して返す。"""
            text = item.get("text", "")
            text = re.sub(r"\[\[[^\]]+\]\]", "", text)
            return text.strip()

        def split_task_and_memo(
            item: dict,
        ) -> Tuple[str, Optional[str]]:
            """
            「子タスク名 @メモ」をタスク名とメモに分割する。

            最初の@より前をタスク名、後ろをメモとして扱う。
            """
            text = clean_item_text(item)
            task_text, separator, memo_text = text.partition("@")

            task_text = task_text.strip()
            memo_text = memo_text.strip() if separator else None

            return task_text, memo_text or None

        # 親タスク直下に従来形式のtype=memoがある場合は、
        # 共通メモとして従来どおり扱う。
        parent_memos = []
        task_children = []

        for child in raw_children:
            if not isinstance(child, dict):
                continue

            child_type = child.get("type", "task")

            if child_type == "memo":
                memo_text = clean_item_text(child)

                if memo_text and memo_text not in parent_memos:
                    parent_memos.append(memo_text)

            elif child_type == "task" and clean_item_text(child):
                task_children.append(child)

        # --- 同名の子タスクを集約 ---
        # 同名タスクの出現回数を数え、メモは重複排除する。
        grouped_children = {}

        for child in task_children:
            child_text, inline_memo = split_task_and_memo(child)

            if not child_text:
                continue

            if child_text not in grouped_children:
                grouped_children[child_text] = {
                    "text": child_text,
                    "count": 0,
                    "memos": [],
                }

            grouped = grouped_children[child_text]
            grouped["count"] += 1

            # 子タスクと同じ行に書かれた@以降をメモとして追加
            if inline_memo and inline_memo not in grouped["memos"]:
                grouped["memos"].append(inline_memo)

            # 既存のtype=memo形式の子要素も後方互換性のため取り込む。
            # 新しい記法では、メモは子タスクと同じ行の@以降に記述する。
            for memo in child.get("children", []) or []:
                if (
                    not isinstance(memo, dict)
                    or memo.get("type") != "memo"
                ):
                    continue

                memo_text = clean_item_text(memo)

                if memo_text and memo_text not in grouped["memos"]:
                    grouped["memos"].append(memo_text)

        # --- titleの生成 ---
        # 親タスクのtag + 子タスク一覧
        # 同名の子タスクが複数ある場合はNセット表記にする。
        children_texts = [
            (
                f"{child['text']} {child['count']}セット"
                if child["count"] > 1
                else child["text"]
            )
            for child in grouped_children.values()
        ]

        children_str = ", ".join(children_texts)

        title = (
            f"{tag}: {children_str}"
            if children_str
            else tag
        )

        # --- descriptionの生成 ---
        # タスクと、そのタスクに紐づくメモを別セクションにする。
        description_lines = []

        if grouped_children:
            description_lines.append("【タスク】")

            for child in grouped_children.values():
                task_label = child["text"]

                if child["count"] > 1:
                    task_label += f"（{child['count']}セット）"

                description_lines.append(f"- {task_label}")

        # 子タスクごとのメモ
        task_memo_lines = []

        for child in grouped_children.values():
            for memo_text in child["memos"]:
                task_memo_lines.append(
                    f"- {child['text']}: {memo_text}"
                )

        if task_memo_lines:
            if description_lines:
                description_lines.append("")

            description_lines.append("【メモ】")
            description_lines.extend(task_memo_lines)

        # 親タスク直下に従来形式の共通メモがある場合は表示する。
        if parent_memos:
            if description_lines:
                description_lines.append("")

            description_lines.append("【共通メモ】")
            description_lines.extend(
                f"- {memo}" for memo in parent_memos
            )

        description = "\n".join(description_lines)

        # --- 時間指定の割り込み処理 ---
        node_start_time = node.get("start_time")

        if node_start_time:
            try:
                hour_str, min_str = node_start_time.split(":")

                # current_timeの日付ではなく、
                # 基準日(base_date)に対して時刻をセットする。
                target_time = datetime.strptime(
                    f"{hour_str}:{min_str}",
                    "%H:%M",
                ).time()

                current_time = datetime.combine(
                    base_date,
                    target_time,
                ).replace(tzinfo=tz)

            except ValueError:
                pass

        duration = timedelta(minutes=node["minutes"])
        end_time = current_time + duration

        # 色の決定
        if tag in focus_tags:
            event_color = "RED"
        else:
            event_color = TAG_COLOR_MAP.get(tag)

        target_cal_key = TAG_CALENDAR_MAP.get(
            tag,
            default_calendar_key,
        )

        event_payload = {
            "title": title,
            "start": current_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": description,
            "color": event_color,
        }

        events_by_calendar.setdefault(
            target_cal_key,
            [],
        ).append(event_payload)

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
                    print(
                        f"✅ 【{cal_key}】 ({len(events)} 件) "
                        "Googleカレンダーへの登録成功！"
                    )
                else:
                    print(
                        f"⚠️ 【{cal_key}】 GAS側エラー: "
                        f"{res_json.get('error')}"
                    )
            else:
                status_code = (
                    response.status_code
                    if response
                    else "No Response"
                )
                print(
                    f"❌ 【{cal_key}】 HTTP通信エラー: {status_code}"
                )

        except Exception as e:
            print(f"❌ 【{cal_key}】 送信例外発生: {e}")

    print("カレンダー登録処理が完了しました")
    print("=" * 60)


def register_tasks_by_date(
    target_date: str,
    start_hour_min: str = "15:00",
    target_heading: str = "Today's Tasks",
    sunday_first: bool = False,
) -> None:
    """日付指定でMarkdownからタスクを読み込み、GASへ登録するラッパー関数"""

    if not DAILY_DIR:
        print(
            "❌ エラー: 環境変数 DAILY_NOTE_DIR が設定されていません。"
        )
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

    # 1. 個別ノートを先にリストに追加
    if os.path.exists(file_path):
        target_files.append(file_path)
    else:
        print(
            "⚠️ 指定日のノートが存在しないため、"
            f"DAILY_TASK のみを処理対象とします: {file_path}"
        )

    # 2. DAILY_TASK（ルーティン）を後にリストに追加
    if DAILY_TASK and os.path.exists(DAILY_TASK):
        target_files.append(DAILY_TASK)

    if not target_files:
        print(
            "❌ 処理対象のファイル"
            "（DAILY_TASK / 個別ノート）が存在しません。"
        )
        return

    register_tasks_from_markdown_to_calendar(
        file_path=target_files,
        target_heading=target_heading,
        weekly_dir=WEEKLY_DIR or DAILY_DIR,
        start_time=start_time_str,
        sunday_first=sunday_first,
    )
