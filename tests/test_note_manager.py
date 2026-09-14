from datetime import datetime
from unittest.mock import patch

from app.notes.note_manager import (
    get_daily_template_spec,
    create_dailynote,
    create_next_weekly_note,
)


def test_get_daily_template_spec(monkeypatch):
    monkeypatch.setenv("DAILY_NOTE_TEMPLATE", "default.md")
    monkeypatch.setenv("DAILY_NOTE_TEMPLATE_MONDAY", "monday.md")

    result = get_daily_template_spec()

    assert result == "default.md"


def test_create_dailynote(monkeypatch):
    monkeypatch.setenv("DAILY_NOTE_DIR", "dummy_daily_dir")

    start_date = datetime(2026, 9, 8)

    template_spec = {
        "default": "default.md",
    }

    with patch(
        "app.notes.note_manager.get_daily_template_spec",
        return_value=template_spec,
    ), patch(
        "app.notes.note_manager.NoteGenerator.batch_create_dailies"
    ) as mock_batch:

        create_dailynote(start_date=start_date)

    mock_batch.assert_called_once_with(
        output_dir="",
        start_date=start_date,
        days_count=7,
        template_spec=template_spec,
    )


def test_create_next_weekly_note(monkeypatch):
    monkeypatch.setenv("WEEKLY_NOTE_DIR", "dummy_weekly_dir")
    monkeypatch.setenv("WEEKLY_NOTE_TEMPLATE", "dummy_template.md")
    monkeypatch.setenv("PLAN_NOTE_DIR", "dummy_plan_dir")

    with patch(
        "app.notes.note_manager.NoteGenerator.create_weekly_note"
    ) as mock_create:

        create_next_weekly_note()

    mock_create.assert_called_once()

    kwargs = mock_create.call_args.kwargs

    assert kwargs["output_dir"] == ""
    assert kwargs["template_path"] == "dummy_template.md"
    assert kwargs["plan_dir"] == "dummy_plan_dir"
    assert kwargs["start_of_week"] == "monday"
    assert isinstance(kwargs["target_date"], datetime)
