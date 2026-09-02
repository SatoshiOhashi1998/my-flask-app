# test_use_md_file.py
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.modules.use_md_file import (
    get_focus_tags_from_weekly_note,
    register_tasks_from_markdown_to_calendar,
    get_daily_template_spec,
    create_dailynote,
    create_next_weekly_note,
)
from myutils.markdown.note_processor import NoteParser, NoteGenerator


# ==========================================
# 1. Weekly Noteからのタグ抽出テスト
# ==========================================

def test_get_focus_tags_success(tmp_path):
    weekly_dir = tmp_path
    note_path = weekly_dir / "2026-W36.md"

    content = """# 今週の予定
# 頑張りたいことを書き出す
- [ ] 運動
- 読書
"""
    note_path.write_text(content, encoding="utf-8")

    target_date = datetime(2026, 8, 31, 9, 0)

    tags = get_focus_tags_from_weekly_note(
        str(weekly_dir),
        target_date,
    )

    assert tags == ["運動", "読書"]


# ==========================================
# 2. カレンダー登録
#    （複数ファイル結合 ＆ 子タスク結合）
# ==========================================

@patch("app.modules.test.use_md_file.send_to_gas")
@patch("app.modules.test.use_md_file.NoteParser")
@patch("app.modules.test.use_md_file.get_focus_tags_from_weekly_note")
def test_register_tasks_multiple_files_and_children(
    mock_get_focus,
    mock_note_parser,
    mock_send_gas,
    tmp_path,
):
    # ------------------------------------------
    # 準備
    # ------------------------------------------

    mock_get_focus.return_value = ["運動"]

    # 2つのダミーファイルを作成
    file1 = tmp_path / "daily_note.md"
    file2 = tmp_path / "daily_task.md"

    file1.write_text("# Tasks", encoding="utf-8")
    file2.write_text("# Tasks", encoding="utf-8")

    # ------------------------------------------
    # NoteParser のインスタンスmockを準備
    # ------------------------------------------

    parser1 = MagicMock()
    parser1.get_heading_task_tree.return_value = [
        {
            "tag": "運動",
            "minutes": 30,
            "start_time": "08:00",
            "children": [
                {"text": "ジョギング [[Obsidianリンク]]"},
                {"text": "ストレッチ"},
            ],
        }
    ]

    parser2 = MagicMock()
    parser2.get_heading_task_tree.return_value = [
        {
            "tag": "仕事",
            "minutes": 60,
            "start_time": None,
            "children": [
                {"text": "メール確認"},
            ],
        }
    ]

    # NoteParser(...) が呼ばれたとき、
    # file1ならparser1、file2ならparser2を返す
    def note_parser_side_effect(note):
        if note.file_path == str(file1):
            return parser1

        if note.file_path == str(file2):
            return parser2

        raise AssertionError(
            f"想定外のファイルパスです: {note.file_path}"
        )

    mock_note_parser.side_effect = note_parser_side_effect

    # ------------------------------------------
    # GAS送信mock
    # ------------------------------------------

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_send_gas.return_value = mock_response

    # ------------------------------------------
    # 実行
    # ------------------------------------------

    register_tasks_from_markdown_to_calendar(
        file_path=[str(file1), str(file2)],
        target_heading="Tasks",
        weekly_dir=str(tmp_path),
        start_time="2026-08-31 09:00",
        default_calendar_key="Daily Life",
    )

    # ------------------------------------------
    # 検証
    # ------------------------------------------

    assert mock_send_gas.called

    args, kwargs = mock_send_gas.call_args
    payload = kwargs.get("data")

    assert payload is not None
    assert payload["calendarKey"] == "Daily Life"

    events = payload["data"]

    # file1 + file2 の2件
    assert len(events) == 2

    # ------------------------------------------
    # file1側
    # ------------------------------------------

    assert events[0]["title"] == "運動: ジョギング, ストレッチ"
    assert events[0]["description"] == "- ジョギング\n- ストレッチ"
    assert events[0]["color"] == "RED"

    # ------------------------------------------
    # file2側
    # ------------------------------------------

    assert events[1]["title"] == "仕事: メール確認"
    assert events[1]["color"] == "GREEN"

    # get_heading_task_tree が各parserで正しく呼ばれたこと
    parser1.get_heading_task_tree.assert_called_once_with("Tasks")
    parser2.get_heading_task_tree.assert_called_once_with("Tasks")


# ==========================================
# 3. ノート作成関連
# ==========================================

def test_get_daily_template_spec(monkeypatch):
    # ------------------------------------------
    # 環境変数を設定
    # ------------------------------------------

    monkeypatch.setenv(
        "DAILY_NOTE_TEMPLATE",
        "default_template.md",
    )

    monkeypatch.setenv(
        "DAILY_NOTE_TEMPLATE_MONDAY",
        "monday_template.md",
    )

    # ------------------------------------------
    # 実行
    # ------------------------------------------

    spec = get_daily_template_spec()

    # ------------------------------------------
    # 検証
    # ------------------------------------------

    assert spec["DEFAULT"] == "default_template.md"
    assert spec["MONDAY"] == "monday_template.md"

    # 未設定の曜日はデフォルトへフォールバック
    assert spec["TUESDAY"] == "default_template.md"
    assert spec["WEDNESDAY"] == "default_template.md"
    assert spec["THURSDAY"] == "default_template.md"
    assert spec["FRIDAY"] == "default_template.md"
    assert spec["SATURDAY"] == "default_template.md"
    assert spec["SUNDAY"] == "default_template.md"


@patch(
    "app.modules.test.use_md_file.NoteGenerator.batch_create_dailies"
)
def test_create_dailynote(
    mock_batch_create,
    monkeypatch,
):
    # ------------------------------------------
    # 環境変数
    # ------------------------------------------

    monkeypatch.setenv(
        "DAILY_NOTE_DIR",
        "/dummy/daily_dir",
    )

    # ------------------------------------------
    # 実行
    # ------------------------------------------

    target_date = datetime(2026, 9, 1, 9, 0)

    create_dailynote(target_date)

    # ------------------------------------------
    # 検証
    # ------------------------------------------

    mock_batch_create.assert_called_once()

    _, kwargs = mock_batch_create.call_args

    # 新APIでは Vault が DAILY_NOTE_DIR をルートとして持つため
    # output_dir は空文字列になる
    assert kwargs["output_dir"] == ""

    assert kwargs["start_date"] == target_date
    assert kwargs["days_count"] == 7

    # template_spec が渡されていることも確認
    assert "template_spec" in kwargs

    template_spec = kwargs["template_spec"]

    assert template_spec["DEFAULT"] is None
    assert template_spec["MONDAY"] is None
    assert template_spec["TUESDAY"] is None


@patch(
    "app.modules.test.use_md_file.NoteGenerator.create_weekly_note"
)
def test_create_next_weekly_note(
    mock_create_weekly,
    monkeypatch,
):
    # ------------------------------------------
    # 環境変数
    # ------------------------------------------

    monkeypatch.setenv(
        "WEEKLY_NOTE_DIR",
        "/dummy/weekly_dir",
    )

    monkeypatch.setenv(
        "WEEKLY_NOTE_TEMPLATE",
        "/dummy/weekly_template.md",
    )

    monkeypatch.setenv(
        "PLAN_NOTE_DIR",
        "/dummy/plan_dir",
    )

    # ------------------------------------------
    # 実行
    # ------------------------------------------

    create_next_weekly_note()

    # ------------------------------------------
    # 検証
    # ------------------------------------------

    mock_create_weekly.assert_called_once()

    _, kwargs = mock_create_weekly.call_args

    # 新APIでは Vault が WEEKLY_NOTE_DIR をルートとして持つため
    # output_dir は空文字列になる
    assert kwargs["output_dir"] == ""

    assert kwargs["template_path"] == "/dummy/weekly_template.md"
    assert kwargs["plan_dir"] == "/dummy/plan_dir"
    assert kwargs["start_of_week"] == "monday"

    # target_date が渡されていることを確認
    assert "target_date" in kwargs
    assert isinstance(kwargs["target_date"], datetime)
