import os
import webbrowser

from app import mail
from app.weather import register_tomorrow_weather_to_calendar


def register_others_jobs(scheduler):
    """メール・天気・URL関連のジョブを登録する"""

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

    _register_kiatsu_jobs(scheduler)


def _register_kiatsu_jobs(scheduler):
    """気圧情報のURLを定時に開くジョブを登録する"""

    kiatsu_url = os.getenv("KIATSU_URL")

    for hour in [9, 12, 15, 18, 22]:
        scheduler.add_job(
            func=webbrowser.open,
            trigger="cron",
            hour=hour,
            minute=0,
            args=[kiatsu_url],
            job_id=f"kiatsu_job_{hour}",
        )
