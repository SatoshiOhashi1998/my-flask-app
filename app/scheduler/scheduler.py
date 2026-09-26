import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .markdown_jobs import register_markdown_jobs
from .others_jobs import register_others_jobs

logger = logging.getLogger(__name__)


class Scheduler:
    """PersonalHubの定期実行処理を管理するScheduler"""

    def __init__(self, app=None):
        self.app = app

        self.scheduler = BackgroundScheduler(
            max_instances=1,
            misfire_grace_time=60,
        )
        self.scheduler.start()

        register_markdown_jobs(
            scheduler=self,
            app=self.app,
        )

        register_others_jobs(
            scheduler=self,
        )

    def add_job(self, func, trigger, job_id, **kwargs):
        self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            **kwargs,
        )

        logger.info(
            "ジョブ %s を追加しました。",
            job_id,
        )

    def remove_job(self, job_id):
        try:
            self.scheduler.remove_job(job_id)

            logger.info(
                "ジョブ %s を削除しました。",
                job_id,
            )

        except Exception as e:
            logger.error(
                "ジョブ %s の削除に失敗しました: %s",
                job_id,
                e,
            )

    def get_job_list(self):
        jobs = self.scheduler.get_jobs()

        return [
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
