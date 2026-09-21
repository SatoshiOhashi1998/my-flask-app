import logging

from app.notes.export_comments import export_today_comments_to_md
from app.notes.note_manager import (
    create_dailynote,
    create_next_weekly_note,
    add_thino_summary_to_weekly_note,
    add_comment_summary_to_weekly_note,
)

logger = logging.getLogger(__name__)


def _run_with_app_context(app, func, func_name):
    if app is None:
        logger.warning(
            "%s: Flask appが指定されていません。"
            "application contextなしで実行します。",
            func_name,
        )
        return func()

    logger.info(
        "%s: app_contextを使用して実行します。",
        func_name,
    )

    with app.app_context():
        return func()


def export_comments_job(app):
    logger.info(
        "export_today_comments_to_md() を開始します。"
    )

    try:
        result = _run_with_app_context(
            app=app,
            func=export_today_comments_to_md,
            func_name="export_today_comments_to_md",
        )

        logger.info(
            "export_today_comments_to_md() が完了しました。"
        )

        return result

    except Exception:
        logger.exception(
            "export_today_comments_to_md() の実行中にエラーが発生しました。"
        )
        raise


def add_thino_summary_job(app):
    logger.info(
        "add_thino_summary_to_weekly_note() を開始します。"
    )

    try:
        result = _run_with_app_context(
            app=app,
            func=add_thino_summary_to_weekly_note,
            func_name="add_thino_summary_to_weekly_note",
        )

        logger.info(
            "add_thino_summary_to_weekly_note() が完了しました。"
        )

        return result

    except Exception:
        logger.exception(
            "add_thino_summary_to_weekly_note() の実行中にエラーが発生しました。"
        )
        raise


def add_comment_summary_job(app):
    logger.info(
        "add_comment_summary_to_weekly_note() を開始します。"
    )

    try:
        result = _run_with_app_context(
            app=app,
            func=add_comment_summary_to_weekly_note,
            func_name="add_comment_summary_to_weekly_note",
        )

        logger.info(
            "add_comment_summary_to_weekly_note() が完了しました。"
        )

        return result

    except Exception:
        logger.exception(
            "add_comment_summary_to_weekly_note() の実行中にエラーが発生しました。"
        )
        raise


def register_markdown_jobs(scheduler, app=None):
    scheduler.add_job(
        func=export_comments_job,
        trigger="cron",
        hour=22,
        minute=0,
        job_id="export_today_comments_22_hour",
        args=[app],
    )

    scheduler.add_job(
        func=export_comments_job,
        trigger="cron",
        hour=23,
        minute=55,
        job_id="export_today_comments_23_hour",
        args=[app],
    )

    scheduler.add_job(
        func=create_dailynote,
        trigger="cron",
        hour=18,
        minute=0,
        job_id="create_daily_notes",
    )

    scheduler.add_job(
        func=create_next_weekly_note,
        trigger="cron",
        day_of_week="sat",
        hour=23,
        minute=0,
        job_id="create_next_weekly_note",
    )

    scheduler.add_job(
        func=add_thino_summary_job,
        trigger="cron",
        day_of_week="sat",
        hour=23,
        minute=0,
        job_id="add_thino_summary_to_weekly_note",
        args=[app],
    )

    scheduler.add_job(
        func=add_comment_summary_job,
        trigger="cron",
        day_of_week="sat",
        hour=23,
        minute=0,
        job_id="add_comment_summary_to_weekly_note",
        args=[app],
    )
