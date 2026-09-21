import os
import webbrowser

from dataclasses import dataclass

from app import mail
from app.weather import register_tomorrow_weather_to_calendar


@dataclass
class UrlJob:
    """URLジョブを管理するデータクラス"""

    url: str
    job_id: str


def register_others_jobs(scheduler):
    url_jobs = [
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

    _register_url_jobs(
        scheduler=scheduler,
        url_jobs=url_jobs,
    )

    scheduler.add_job(
        func=mail.check_email,
        trigger="interval",
        minutes=5,
        job_id="check_email",
    )

    scheduler.add_job(
        func=register_tomorrow_weather_to_calendar,
        trigger="cron",
        hour=23,
        minute=0,
        job_id="get_weather_data",
    )


def _register_url_jobs(scheduler, url_jobs):
    weather_job = next(
        job
        for job in url_jobs
        if job.job_id == "weather_job"
    )

    kiatsu_job = next(
        job
        for job in url_jobs
        if job.job_id == "kiatsu_job"
    )

    scheduler.add_job(
        func=webbrowser.open,
        trigger="cron",
        hour=0,
        minute=5,
        args=[weather_job.url],
        job_id=f"{weather_job.job_id}_0",
    )

    scheduler.add_job(
        func=webbrowser.open,
        trigger="cron",
        hour=0,
        minute=5,
        args=[kiatsu_job.url],
        job_id=f"{kiatsu_job.job_id}_0",
    )

    for hour in [9, 12, 18]:
        scheduler.add_job(
            func=webbrowser.open,
            trigger="cron",
            hour=hour,
            minute=0,
            args=[weather_job.url],
            job_id=f"{weather_job.job_id}_{hour}",
        )
