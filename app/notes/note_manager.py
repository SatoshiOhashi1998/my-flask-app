import os
from datetime import datetime, timedelta

from myutils.markdown.note_processor import Vault, NoteGenerator
from myutils.markdown.thino import collect_thino_links
from myutils.markdown.utils import MarkdownUtils
from app.notes.export_comments import collect_comment_links

THINO_HEADING = "Thino"
THINO_SUMMARY_HEADING = "Thino Summary"
COMMENT_SUMMARY_HEADING = "Comment Summary"

WEEKLY_NOTE_START_OF_WEEK = "monday"
SUMMARY_START_OF_WEEK = "sunday"

def _get_weekly_summary_context(target_date=None):
    """
    Weekly Note の対象週と、Summary の集計期間を取得する。

    Weekly Note:
        月曜日〜日曜日

    Summary:
        Weekly Note の開始日前日（日曜日）〜土曜日
    """
    if target_date is None:
        target_date = datetime.now()

    (
        weekly_start_date,
        weekly_end_date,
        year,
        week_num,
    ) = MarkdownUtils.calculate_week_range(
        target_date,
        start_of_week=WEEKLY_NOTE_START_OF_WEEK,
    )

    # Weekly Note の開始日前日を集計期間の起点にする
    summary_target_date = weekly_start_date - timedelta(days=1)

    return (
        weekly_start_date,
        weekly_end_date,
        year,
        week_num,
        summary_target_date,
    )


def add_thino_summary_to_weekly_note(target_date=None):
    """前日曜日〜土曜日のThino投稿を、対象週のWeekly Noteへ追加する。"""
    daily_dir = os.getenv("DAILY_NOTE_DIR")
    weekly_dir = os.getenv("WEEKLY_NOTE_DIR")

    if not daily_dir:
        raise ValueError(
            "DAILY_NOTE_DIRが環境変数に設定されていません。"
        )

    if not weekly_dir:
        raise ValueError(
            "WEEKLY_NOTE_DIRが環境変数に設定されていません。"
        )

    (
        _,
        _,
        year,
        week_num,
        summary_target_date,
    ) = _get_weekly_summary_context(target_date)

    weekly_file_name = f"{year}-W{week_num:02d}.md"

    weekly_vault = Vault(weekly_dir)
    weekly_note = weekly_vault.get_note(weekly_file_name)

    links = collect_thino_links(
        daily_note_dir=daily_dir,
        target_date=summary_target_date,
        start_of_week=SUMMARY_START_OF_WEEK,
        thino_heading=THINO_HEADING,
    )

    weekly_note.replace_heading_content(
        THINO_SUMMARY_HEADING,
        "\n\n".join(f"#### {link}" for link in links),
    )

def get_daily_template_spec():
    return {
        "MONDAY": os.getenv("DAILY_NOTE_TEMPLATE_MONDAY"),
        "TUESDAY": os.getenv("DAILY_NOTE_TEMPLATE_TUESDAY"),
        "WEDNESDAY": os.getenv("DAILY_NOTE_TEMPLATE_WEDNESDAY"),
        "THURSDAY": os.getenv("DAILY_NOTE_TEMPLATE_THURSDAY"),
        "FRIDAY": os.getenv("DAILY_NOTE_TEMPLATE_FRIDAY"),
        "SATURDAY": os.getenv("DAILY_NOTE_TEMPLATE_SATURDAY"),
        "SUNDAY": os.getenv("DAILY_NOTE_TEMPLATE_SUNDAY"),
    }


def create_dailynote(start_date=None):
    daily_dir = os.getenv("DAILY_NOTE_DIR")

    if not daily_dir:
        raise ValueError("DAILY_NOTE_DIRが環境変数に設定されていません。")

    if start_date is None:
        start_date = datetime.now()

    template_spec = get_daily_template_spec()

    vault = Vault(daily_dir)
    generator = NoteGenerator(vault)

    generator.batch_create_dailies(
        output_dir="",
        start_date=start_date,
        days_count=7,
        template_spec=template_spec,
    )


def create_next_weekly_note():
    weekly_dir = os.getenv("WEEKLY_NOTE_DIR")
    weekly_template = os.getenv("WEEKLY_NOTE_TEMPLATE")
    plan_dir = os.getenv("PLAN_NOTE_DIR")

    if not weekly_dir:
        raise ValueError("WEEKLY_NOTE_DIRが環境変数に設定されていません。")

    if not weekly_template:
        raise ValueError(
            "WEEKLY_NOTE_TEMPLATEが環境変数に設定されていません。"
        )

    target_date = datetime.now() + timedelta(days=7)

    vault = Vault(weekly_dir)
    generator = NoteGenerator(vault)

    generator.create_weekly_note(
        output_dir="",
        target_date=target_date,
        template_path=weekly_template,
        plan_dir=plan_dir,
        start_of_week="monday",
    )

def add_comment_summary_to_weekly_note(target_date=None):
    """前日曜日〜土曜日のコメントを、対象週のWeekly Noteへ追加する。"""
    comment_export_dir = os.getenv("EXPORT_DIR")
    weekly_dir = os.getenv("WEEKLY_NOTE_DIR")

    if not comment_export_dir:
        raise ValueError(
            "EXPORT_DIRが環境変数に設定されていません。"
        )

    if not weekly_dir:
        raise ValueError(
            "WEEKLY_NOTE_DIRが環境変数に設定されていません。"
        )

    (
        _,
        _,
        year,
        week_num,
        summary_target_date,
    ) = _get_weekly_summary_context(target_date)

    weekly_file_name = f"{year}-W{week_num:02d}.md"

    weekly_vault = Vault(weekly_dir)
    weekly_note = weekly_vault.get_note(weekly_file_name)

    links = collect_comment_links(
        comment_export_dir=comment_export_dir,
        target_date=summary_target_date,
        start_of_week=SUMMARY_START_OF_WEEK,
    )

    weekly_note.replace_heading_content(
        COMMENT_SUMMARY_HEADING,
        "\n\n".join(f"#### {link}" for link in links),
    )
