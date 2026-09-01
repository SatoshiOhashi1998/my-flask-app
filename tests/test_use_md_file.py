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
    
    tags = get_focus_tags_from_weekly_note(str(weekly_dir), target_date)
    assert tags == ["運動", "読書"]


# ==========================================
# 2. カレンダー登録（複数ファイル結合 ＆ 子タスク結合のテスト）
# ==========================================

@patch("app.modules.use_md_file.send_to_gas")
@patch("app.modules.use_md_file.get_heading_task_tree")
@patch("app.modules.use_md_file.get_focus_tags_from_weekly_note")
def test_register_tasks_multiple_files_and_children(mock_get_focus, mock_get_tree, mock_send_gas, tmp_path):
    # 準備
    mock_get_focus.return_value = ["運動"]

    # 2つの異なるファイルパスが渡されたときを想定し、
    # それぞれ異なるタスクツリーを返すようにモックを設定
    def mock_get_tree_side_effect(path, heading):
        if "daily_note.md" in path:
            return [
                {
                    "tag": "運動",
                    "minutes": 30,
                    "start_time": "08:00",
                    "children": [
                        {"text": "ジョギング [[Obsidianリンク]]"},
                        {"text": "ストレッチ"}
                    ],
                }
            ]
        elif "daily_task.md" in path:
            return [
                {
                    "tag": "仕事",
                    "minutes": 60,
                    "start_time": None,
                    "children": [{"text": "メール確認"}],
                }
            ]
        return []

    mock_get_tree.side_effect = mock_get_tree_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_send_gas.return_value = mock_response

    # ダミーのファイルを作成（os.path.existsを通すため）
    file1 = tmp_path / "daily_note.md"
    file2 = tmp_path / "daily_task.md"
    file1.write_text("# Tasks", encoding="utf-8")
    file2.write_text("# Tasks", encoding="utf-8")

    # 実行: リスト形式で複数ファイルを渡す
    register_tasks_from_markdown_to_calendar(
        file_path=[str(file1), str(file2)],
        target_heading="Tasks",
        weekly_dir=str(tmp_path),
        start_time="2026-08-31 09:00",
        default_calendar_key="Daily Life",
    )

    # 検証
    assert mock_send_gas.called
    args, kwargs = mock_send_gas.call_args
    payload = kwargs.get("data")
    
    events = payload["data"]
    
    # file1 と file2 のタスクが正しく結合（2件）されているか
    assert len(events) == 2

    # 1. file1側: 複数ある子タスクがコンマ区切りで結合され、Obsidianリンクが消えているか
    assert events[0]["title"] == "運動: ジョギング, ストレッチ"
    assert events[0]["description"] == "- ジョギング\n- ストレッチ"
    assert events[0]["color"] == "RED"  # focus_tags に含まれるため

    # 2. file2側: ルーティン側のタスクが正しく後に続いているか
    assert events[1]["title"] == "仕事: メール確認"
    assert events[1]["color"] == "GREEN"  # TAG_COLOR_MAP による

# ==========================================
# 3. ノート作成関連のテスト
# ==========================================

def test_get_daily_template_spec(monkeypatch):
    # 環境変数を設定してテンプレート仕様の辞書が正しく構築されるか
    monkeypatch.setenv("DAILY_NOTE_TEMPLATE", "default_template.md")
    monkeypatch.setenv("DAILY_NOTE_TEMPLATE_MONDAY", "monday_template.md")

    spec = get_daily_template_spec()
    assert spec["DEFAULT"] == "default_template.md"
    assert spec["MONDAY"] == "monday_template.md"
    assert spec["TUESDAY"] == "default_template.md"  # 未設定の曜日はデフォルトにフォールバック


@patch("app.modules.use_md_file.batch_create_dailies_from_file")
def test_create_dailynote(mock_batch_create, monkeypatch):
    # 環境変数とデイリーノート生成関数のモック化
    monkeypatch.setenv("DAILY_NOTE_DIR", "/dummy/daily_dir")

    target_date = datetime(2026, 9, 1, 9, 0)
    create_dailynote(target_date)

    mock_batch_create.assert_called_once()
    _, kwargs = mock_batch_create.call_args
    assert kwargs["output_dir"] == "/dummy/daily_dir"
    assert kwargs["start_date"] == target_date
    assert kwargs["days_count"] == 7


@patch("app.modules.use_md_file.create_weekly_note")
def test_create_next_weekly_note(mock_create_weekly, monkeypatch):
    # 環境変数とウィークリーノート生成関数のモック化
    monkeypatch.setenv("WEEKLY_NOTE_DIR", "/dummy/weekly_dir")
    monkeypatch.setenv("WEEKLY_NOTE_TEMPLATE", "/dummy/weekly_template.md")
    monkeypatch.setenv("PLAN_NOTE_DIR", "/dummy/plan_dir")

    create_next_weekly_note()

    mock_create_weekly.assert_called_once()
    _, kwargs = mock_create_weekly.call_args
    assert kwargs["output_dir"] == "/dummy/weekly_dir"
    assert kwargs["template_path"] == "/dummy/weekly_template.md"
    assert kwargs["plan_dir"] == "/dummy/plan_dir"
    assert kwargs["start_of_week"] == "monday"
