import os
import logging
import webbrowser
import subprocess
from dataclasses import dataclass
from apscheduler.schedulers.background import BackgroundScheduler
from app.modules import useMailServer
from app.modules.getWeatherData import register_tomorrow_weather_to_calendar
from app.modules.getYouTubeLive import send_archived_streams_from_excel_channels
from app.modules.export_comments import export_today_comments_to_md

logger = logging.getLogger(__name__)  # モジュール専用ロガー

@dataclass
class UrlJob:
    """URLジョブを管理するデータクラス"""
    url: str
    job_id: str


class UrlScheduler:
    """URLのスケジュール管理を行うクラス"""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = BackgroundScheduler(max_instances=1)
        self.scheduler.start()

        self.url_jobs = [
            UrlJob(url=os.getenv('DYNALIST_URL'), job_id="target_job"),
            UrlJob(url=os.getenv('TENKI_URL'), job_id="weather_job"),
            UrlJob(url=os.getenv('KIATSU_URL'), job_id="kiatsu_job"),
            UrlJob(url=os.getenv('ILLUST_LIST_URL'), job_id="illust_job")
        ]

        self.schedule_url_jobs()

        self.add_job(
            func=useMailServer.check_email,
            trigger="interval",
            minutes=5,
            job_id="check_email"
        )

        self.add_job(
            func=register_tomorrow_weather_to_calendar,
            trigger='cron',
            hour=23,
            minute=0,
            job_id="get_weather_data"
        )

        # アプリコンテキストを付与して呼び出すラッパー関数
        def run_export_comments():
            if self.app:
                with self.app.app_context():
                    export_today_comments_to_md()
            else:
                export_today_comments_to_md()

        # 毎日23:55に本日のコメントをMarkdownに出力するジョブ
        self.add_job(
            func=run_export_comments,
            trigger='cron',
            hour=23,
            minute=55,
            job_id="export_today_comments"
        )

    def schedule_url_jobs(self):
        """特定のURLを指定の時間に開くジョブをスケジュール"""
        self.add_job(
            webbrowser.open,
            'cron',
            hour=0,
            minute=5,
            args=[self.url_jobs[1].url],
            job_id=f"{self.url_jobs[1].job_id}_{0}"
        )
        self.add_job(
            webbrowser.open,
            'cron',
            hour=0,
            minute=5,
            args=[self.url_jobs[2].url],
            job_id=f"{self.url_jobs[2].job_id}_{0}"
        )
        for hour in [9, 12, 18]:
            self.add_job(
                webbrowser.open,
                'cron',
                hour=hour,
                minute=0,
                args=[self.url_jobs[1].url],
                job_id=f"{self.url_jobs[1].job_id}_{hour}"
            )

    def add_job(self, func, trigger, job_id, **kwargs):
        """ジョブ追加メソッド"""
        self.scheduler.add_job(func, trigger, id=job_id, **kwargs)
        logger.info(f"ジョブ {job_id} を追加しました。")

    def remove_job(self, job_id):
        """指定IDのジョブを削除"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"ジョブ {job_id} を削除しました。")
        except Exception as e:
            logger.error(f"ジョブ {job_id} の削除に失敗しました: {e}")

    def get_job_list(self):
        """追加されているジョブの一覧をJSON形式で取得"""
        jobs = self.scheduler.get_jobs()
        job_list = [
            {
                "job_id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
        return job_list
