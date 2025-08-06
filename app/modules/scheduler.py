"""
URL スケジューラー

このモジュールは、指定されたURLを特定の時間に自動的に開くためのスケジュール管理機能を提供します。
また、メールサーバーのチェックや定期的に実行するバッチファイルの管理も行います。

使用方法:
1. UrlScheduler クラスをインスタンス化します。
2. スケジュールされたジョブがバックグラウンドで実行されます。
3. 必要に応じてジョブの追加、削除、取得を行うことができます。

依存関係:
- logging: ログ出力のための標準ライブラリ。
- webbrowser: デフォルトのウェブブラウザを使用してURLを開くための標準ライブラリ。
- dataclasses: データクラスの作成をサポートする標準ライブラリ。
- apscheduler: スケジュール管理のためのサードパーティライブラリ。
- app.useMailServer: メールサーバーのチェック機能を提供するモジュール。
- subprocess: 新しいプロセスを生成するための標準ライブラリ。
"""

import os
import logging
import webbrowser
from dataclasses import dataclass
from apscheduler.schedulers.background import BackgroundScheduler
from app.modules import useMailServer
import subprocess

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

        # スケジュールするURLとそれに対応するジョブIDをデータクラスのインスタンスとして定義
        self.url_jobs = [
            UrlJob(url=os.getenv('DYNALIST_URL'), job_id="target_job"),
            UrlJob(url=os.getenv('TENKI_URL'), job_id="weather_job"),
            UrlJob(url=os.getenv('ILLUST_LIST_URL'), job_id="illust_job")
        ]

        # スケジュールジョブの登録
        self.schedule_url_jobs()

        # メールサーバー確認ジョブ
        self.add_job(func=useMailServer.check_email, trigger="interval", minutes=5, job_id="check_email")

        # 各種batファイルの起動
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
        # for hour in range(24):
        #     self.add_job(webbrowser.open, 'cron', hour=hour, minute=0, args=[self.url_jobs[0].url], job_id=f"{self.url_jobs[0].job_id}_{hour}")

        for hour in [0, 9, 12, 18]:
            self.add_job(webbrowser.open, 'cron', hour=hour, minute=0, args=[self.url_jobs[1].url], job_id=f"{self.url_jobs[1].job_id}_{hour}")

        # self.add_job(webbrowser.open, 'cron', hour=18, minute=0, args=[self.url_jobs[2].url], job_id=self.url_jobs[2].job_id)

    def add_job(self, func, trigger, job_id, **kwargs):
        """ジョブ追加メソッド"""
        self.scheduler.add_job(func, trigger, id=job_id, **kwargs)

    def remove_job(self, job_id):
        """指定IDのジョブを削除"""
        try:
            self.scheduler.remove_job(job_id)
            logging.info(f"ジョブ {job_id} を削除しました。")
        except Exception as e:
            logging.error(f"ジョブ {job_id} の削除に失敗しました: {e}")

    def get_job_list(self):
        """追加されているジョブの一覧をJSON形式で取得"""
        jobs = self.scheduler.get_jobs()
        job_list = [
            {"job_id": job.id, "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None}
            for job in jobs
        ]
        return job_list
