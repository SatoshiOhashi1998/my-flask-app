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
    """Flask application context内で関数を実行する。"""

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
    """当日のコメントをMarkdownへ出力する。"""

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

def update_weekly_note_job(app):
    """翌週のWeekly Noteを作成し、各Summaryを追加する。"""

    logger.info(
        "update_weekly_note_job() を開始します。"
    )

    def update_weekly_note():
        logger.info(
            "create_next_weekly_note() を開始します。"
        )
        create_next_weekly_note()
        logger.info(
            "create_next_weekly_note() が完了しました。"
        )

        logger.info(
            "add_thino_summary_to_weekly_note() を開始します。"
        )
        add_thino_summary_to_weekly_note()
        logger.info(
            "add_thino_summary_to_weekly_note() が完了しました。"
        )

        logger.info(
            "add_comment_summary_to_weekly_note() を開始します。"
        )
        add_comment_summary_to_weekly_note()
        logger.info(
            "add_comment_summary_to_weekly_note() が完了しました。"
        )

    try:
        result = _run_with_app_context(
            app=app,
            func=update_weekly_note,
            func_name="update_weekly_note",
        )

        logger.info(
            "update_weekly_note_job() が完了しました。"
        )

        return result

    except Exception:
        logger.exception(
            "update_weekly_note_job() の実行中にエラーが発生しました。"
        )
        raise

def register_markdown_jobs(scheduler, app=None):
    """Markdown関連の定期実行Jobを登録する。"""

    # 当日のコメントをMarkdownへ出力
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

    # Daily Noteを作成
    scheduler.add_job(
        func=create_dailynote,
        trigger="cron",
        hour=18,
        minute=0,
        job_id="create_daily_notes",
    )

    # Weekly Noteを作成し、Summaryを追加
    scheduler.add_job(
        func=update_weekly_note_job,
        trigger="cron",
        day_of_week="sat",
        hour=23,
        minute=0,
        job_id="update_weekly_note",
        args=[app],
    )
