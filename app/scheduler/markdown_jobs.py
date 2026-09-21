import logging


from app.notes.export_comments import (
    export_today_comments_to_md,
)
from app.notes.note_manager import (
    create_dailynote,
    create_next_weekly_note,
    add_thino_summary_to_weekly_note,
    add_comment_summary_to_weekly_note,
)


logger = logging.getLogger(__name__)


def _run_with_app_context(app, func, func_name):
    """Flask application context内でジョブを実行する"""

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


def _run_export_comments(app):
    """当日のコメントをMarkdownへ出力する"""

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
            "export_today_comments_to_md() "
            "の実行中にエラーが発生しました。"
        )
        raise


def _run_add_thino_summary(app):
    """Weekly NoteへThino Summaryを追加する"""

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
            "add_thino_summary_to_weekly_note() "
            "の実行中にエラーが発生しました。"
        )
        raise


def _run_add_comment_summary(app):
    """Weekly NoteへComment Summaryを追加する"""

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
            "add_comment_summary_to_weekly_note() "
            "の実行中にエラーが発生しました。"
        )
        raise


def register_markdown_jobs(scheduler, app=None):
    """Markdown関連のジョブを登録する"""

    # ---------------------------------------------------------
    # コメントMarkdown出力
    # ---------------------------------------------------------

    # 毎日22:00
    scheduler.add_job(
        func=lambda: _run_export_comments(app),
        trigger="cron",
        hour=22,
        minute=0,
        id="export_today_comments_22_hour",
    )

    # 毎日23:55
    scheduler.add_job(
        func=lambda: _run_export_comments(app),
        trigger="cron",
        hour=23,
        minute=55,
        id="export_today_comments_23_hour",
    )

    # ---------------------------------------------------------
    # Daily Note作成
    # ---------------------------------------------------------

    scheduler.add_job(
        func=create_dailynote,
        trigger="cron",
        hour=18,
        minute=0,
        id="create_daily_notes",
    )

    # ---------------------------------------------------------
    # Weekly Note作成
    # ---------------------------------------------------------

    # 毎週土曜日23:00に翌週のWeekly Noteを作成
    scheduler.add_job(
        func=create_next_weekly_note,
        trigger="cron",
        day_of_week="sat",
        hour=23,
        minute=0,
        id="create_next_weekly_note",
    )

    # ---------------------------------------------------------
    # Thino Summary
    # ---------------------------------------------------------

    scheduler.add_job(
        func=lambda: _run_add_thino_summary(app),
        trigger="cron",
        day_of_week="sat",
        hour=23,
        minute=0,
        id="add_thino_summary_to_weekly_note",
    )

    # ---------------------------------------------------------
    # Comment Summary
    # ---------------------------------------------------------

    # 毎週土曜日23:00に今週のコメントを
    # 今週のWeekly Noteへ追加
    scheduler.add_job(
        func=lambda: _run_add_comment_summary(app),
        trigger="cron",
        day_of_week="sat",
        hour=23,
        minute=0,
        id="add_comment_summary_to_weekly_note",
    )
