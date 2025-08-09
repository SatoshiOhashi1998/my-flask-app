import os
import logging
import webbrowser
import subprocess
from dataclasses import dataclass
from apscheduler.schedulers.background import BackgroundScheduler
from app.modules import useMailServer

logger = logging.getLogger(__name__)  # モジュール専用ロガー

@dataclass
class UrlJob:
    """URLジョブを管理するデータクラス"""
    url: str
    job_id: str


class UrlScheduler:
    """URLのスケジュール管理を行うクラス"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(max_instances=1)
        self.scheduler.start()

        # スケジュールするURLとジョブIDを設定
        self.url_jobs = [
            UrlJob(url=os.getenv('DYNALIST_URL'), job_id="target_job"),
            UrlJob(url=os.getenv('TENKI_URL'), job_id="weather_job"),
            UrlJob(url=os.getenv('ILLUST_LIST_URL'), job_id="illust_job")
        ]

        # ジョブ登録
        self.schedule_url_jobs()

        # メールサーバー確認ジョブ
        self.add_job(
            func=useMailServer.check_email,
            trigger="interval",
            minutes=5,
            job_id="check_email"
        )

        # 各種batファイル起動ジョブ
        self.add_job(
            func=subprocess.Popen,
            args=[os.getenv('GET_WEATHER_DATA_BAT_PATH')],
            trigger='cron',
            hour=23,
            minute=0,
            job_id="get_weather_data"
        )

        self.add_job(
            func=subprocess.Popen,
            args=[os.getenv('GET_YL_ARCHIVE_BAT_PATH')],
            trigger='cron',
            hour=19,
            minute=0,
            job_id="get_YlArchive_data"
        )

    def schedule_url_jobs(self):
        """特定のURLを指定の時間に開くジョブをスケジュール"""
        for hour in [0, 9, 12, 18]:
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
