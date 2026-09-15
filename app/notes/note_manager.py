import os
from datetime import datetime, timedelta

from myutils.markdown.note_processor import Vault, NoteGenerator
from myutils.markdown.thino import collect_thino_links
from myutils.markdown.utils import MarkdownUtils

THINO_HEADING = "Thino"
THINO_SUMMARY_HEADING = "Thino Summary"
START_OF_WEEK = "monday"


def add_thino_summary_to_weekly_note(
    target_date=None,
    start_of_week=START_OF_WEEK,
):
    """
    指定した週のDaily NoteからThino投稿を取得し、
    Weekly Noteの「Thino Summary」を更新する。
    """
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

    if target_date is None:
        target_date = datetime.now()

    if start_of_week not in ("monday", "sunday"):
        raise ValueError(
            "start_of_weekは'monday'または'sunday'を指定してください。"
        )

    (
        start_date,
        end_date,
        year,
        week_num,
    ) = MarkdownUtils.calculate_week_range(
        target_date,
        start_of_week=start_of_week,
    )

    weekly_file_name = f"{year}-W{week_num:02d}.md"

    weekly_vault = Vault(weekly_dir)
    weekly_note = weekly_vault.get_note(weekly_file_name)

    links = collect_thino_links(
        daily_note_dir=daily_dir,
        target_date=target_date,
        start_of_week=start_of_week,
        thino_heading=THINO_HEADING,
    )

    weekly_note.replace_heading_content(
        THINO_SUMMARY_HEADING,
        "\n\n".join(links),
    )


def get_daily_template_spec():
    template_path = os.getenv("DAILY_NOTE_TEMPLATE")

    if not template_path:
        return {
            "default": os.getenv("DAILY_NOTE_TEMPLATE_DEFAULT", ""),
            "monday": os.getenv("DAILY_NOTE_TEMPLATE_MONDAY", ""),
            "tuesday": os.getenv("DAILY_NOTE_TEMPLATE_TUESDAY", ""),
            "wednesday": os.getenv("DAILY_NOTE_TEMPLATE_WEDNESDAY", ""),
            "thursday": os.getenv("DAILY_NOTE_TEMPLATE_THURSDAY", ""),
            "friday": os.getenv("DAILY_NOTE_TEMPLATE_FRIDAY", ""),
            "saturday": os.getenv("DAILY_NOTE_TEMPLATE_SATURDAY", ""),
            "sunday": os.getenv("DAILY_NOTE_TEMPLATE_SUNDAY", ""),
        }

    return template_path


def create_dailynote(start_date=None):
    daily_dir = os.getenv("DAILY_NOTE_DIR")

    if not daily_dir:
        raise ValueError("DAILY_NOTE_DIRが環境変数に設定されていません。")

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
