import os
import logging
import webbrowser
import subprocess

from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler

from app import mail
from app.weather import register_tomorrow_weather_to_calendar
from app.youtube.youtube_live import send_archived_streams_from_excel_channels
from app.notes.export_comments import export_today_comments_to_md
from app.notes.note_manager import (
    create_dailynote,
    create_next_weekly_note,
    add_thino_summary_to_weekly_note,
    add_comment_summary_to_weekly_note,
)


logger = logging.getLogger(__name__)


@dataclass
class UrlJob:
    """URLジョブを管理するデータクラス"""
    url: str
    job_id: str


class UrlScheduler:
    """URLのスケジュール管理を行うクラス"""

    def __init__(self, app=None):
        self.app = app

        self.scheduler = BackgroundScheduler(
            max_instances=1
        )
        self.scheduler.start()

        self.url_jobs = [
            UrlJob(
                url=os.getenv("DYNALIST_URL"),
                job_id="target_job",
            ),
            UrlJob(
                url=os.getenv("TENKI_URL"),
                job_id="weather_job",
            ),
            UrlJob(
                url=os.getenv("KIATSU_URL"),
                job_id="kiatsu_job",
            ),
            UrlJob(
                url=os.getenv("ILLUST_LIST_URL"),
                job_id="illust_job",
            ),
        ]

        self.schedule_url_jobs()

        # ---------------------------------------------------------
        # メールチェック
        # ---------------------------------------------------------
        self.add_job(
            func=mail.check_email,
            trigger="interval",
            minutes=5,
            job_id="check_email",
        )

        # ---------------------------------------------------------
        # 天気情報
        # ---------------------------------------------------------
        self.add_job(
            func=register_tomorrow_weather_to_calendar,
            trigger="cron",
            hour=23,
            minute=0,
            job_id="get_weather_data",
        )

        # ---------------------------------------------------------
        # コメントMarkdown出力
        # ---------------------------------------------------------
        def run_export_comments():
            print(
                "\n===== SCHEDULER: export_comments START ====="
            )

            try:
                if self.app:
                    print(
                        "[SCHEDULER] app_contextを使用します"
                    )

                    with self.app.app_context():
                        export_today_comments_to_md()
                else:
                    print(
                        "[SCHEDULER] self.appがありません"
                    )

                    export_today_comments_to_md()

                print(
                    "[SCHEDULER] export_today_comments_to_md() 完了"
                )

            except Exception:
                logger.exception(
                    "export_today_comments_to_md() "
                    "の実行中にエラーが発生しました"
                )
                raise

            print(
                "===== SCHEDULER: export_comments END =====\n"
            )

        # 毎日22:00
        self.add_job(
            func=run_export_comments,
            trigger="cron",
            hour=22,
            minute=0,
            job_id="export_today_comments_22_hour",
        )

        # 毎日23:55
        self.add_job(
            func=run_export_comments,
            trigger="cron",
            hour=23,
            minute=55,
            job_id="export_today_comments_23_hour",
        )

        # ---------------------------------------------------------
        # Daily Note作成
        # ---------------------------------------------------------
        self.add_job(
            func=create_dailynote,
            trigger="cron",
            hour=18,
            minute=0,
            job_id="create_daily_notes",
        )

        # ---------------------------------------------------------
        # Weekly Note作成
        # ---------------------------------------------------------
        # 毎週土曜日23:00に翌週のWeekly Noteを作成
        self.add_job(
            func=create_next_weekly_note,
            trigger="cron",
            day_of_week="sat",
            hour=23,
            minute=0,
            job_id="create_next_weekly_note",
        )

        # ---------------------------------------------------------
        # Thino Summary
        # ---------------------------------------------------------
        def run_add_thino_summary():
            print(
                "\n===== SCHEDULER: add_thino_summary START ====="
            )

            try:
                if self.app:
                    print(
                        "[SCHEDULER] app_contextを使用します"
                    )

                    with self.app.app_context():
                        add_thino_summary_to_weekly_note()
                else:
                    print(
                        "[SCHEDULER] self.appがありません"
                    )

                    add_thino_summary_to_weekly_note()

                print(
                    "[SCHEDULER] "
                    "add_thino_summary_to_weekly_note() 完了"
                )

            except Exception:
                logger.exception(
                    "add_thino_summary_to_weekly_note() "
                    "の実行中にエラーが発生しました"
                )
                raise

            print(
                "===== SCHEDULER: add_thino_summary END =====\n"
            )

        self.add_job(
            func=run_add_thino_summary,
            trigger="cron",
            day_of_week="sat",
            hour=23,
            minute=0,
            job_id="add_thino_summary_to_weekly_note",
        )

        # ---------------------------------------------------------
        # Comment Summary
        # ---------------------------------------------------------
        def run_add_comment_summary():
            print(
                "\n===== SCHEDULER: "
                "add_comment_summary START ====="
            )

            try:
                if self.app:
                    print(
                        "[SCHEDULER] app_contextを使用します"
                    )

                    with self.app.app_context():
                        add_comment_summary_to_weekly_note()
                else:
                    print(
                        "[SCHEDULER] self.appがありません"
                    )

                    add_comment_summary_to_weekly_note()

                print(
                    "[SCHEDULER] "
                    "add_comment_summary_to_weekly_note() 完了"
                )

            except Exception:
                logger.exception(
                    "add_comment_summary_to_weekly_note() "
                    "の実行中にエラーが発生しました"
                )
                raise

            print(
                "===== SCHEDULER: "
                "add_comment_summary END =====\n"
            )

        # 毎週土曜日23:00に今週のコメントを
        # 今週のWeekly Noteへ追加
        self.add_job(
            func=run_add_comment_summary,
            trigger="cron",
            day_of_week="sat",
            hour=23,
            minute=0,
            job_id="add_comment_summary_to_weekly_note",
        )

    def schedule_url_jobs(self):
        """特定のURLを指定の時間に開くジョブをスケジュール"""

        self.add_job(
            webbrowser.open,
            "cron",
            hour=0,
            minute=5,
            args=[self.url_jobs[1].url],
            job_id=f"{self.url_jobs[1].job_id}_{0}",
        )

        self.add_job(
            webbrowser.open,
            "cron",
            hour=0,
            minute=5,
            args=[self.url_jobs[2].url],
            job_id=f"{self.url_jobs[2].job_id}_{0}",
        )

        for hour in [9, 12, 18]:
            self.add_job(
                webbrowser.open,
                "cron",
                hour=hour,
                minute=0,
                args=[self.url_jobs[1].url],
                job_id=f"{self.url_jobs[1].job_id}_{hour}",
            )

    def add_job(self, func, trigger, job_id, **kwargs):
        """ジョブ追加メソッド"""

        self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            **kwargs,
        )

        logger.info(
            f"ジョブ {job_id} を追加しました。"
        )

    def remove_job(self, job_id):
        """指定IDのジョブを削除"""

        try:
            self.scheduler.remove_job(job_id)

            logger.info(
                f"ジョブ {job_id} を削除しました。"
            )

        except Exception as e:
            logger.error(
                f"ジョブ {job_id} の削除に失敗しました: {e}"
            )

    def get_job_list(self):
        """追加されているジョブの一覧をJSON形式で取得"""

        jobs = self.scheduler.get_jobs()

        job_list = [
            {
                "job_id": job.id,
                "next_run_time": (
                    job.next_run_time.isoformat()
                    if job.next_run_time
                    else None
                ),
            }
            for job in jobs
        ]

        return job_list
