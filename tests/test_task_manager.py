from datetime import datetime
from unittest.mock import patch, MagicMock

from app.modules.task_manager import (
    get_focus_tags_from_weekly_note,
    register_tasks_from_markdown_to_calendar,
)


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

@patch("app.modules.task_manager.send_to_gas")
@patch("app.modules.task_manager.NoteParser")
@patch("app.modules.task_manager.get_focus_tags_from_weekly_note")
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
