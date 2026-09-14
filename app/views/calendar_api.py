import traceback
from datetime import datetime, timedelta

from flask import jsonify, request

from app.modules.getWeatherData import (
    register_today_weather_to_calendar,
    register_tomorrow_weather_to_calendar,
)
from app.modules.task_manager import register_tasks_by_date


def register_calendar_routes(api_bp):
    def _execute_task_sync(
        date_str: str,
        start_time: str,
        target_heading: str = "Today's Tasks",
    ):
        """タスク同期処理の共通実行関数"""
        try:
            register_tasks_by_date(
                target_date=date_str,
                start_hour_min=start_time,
                target_heading=target_heading,
                sunday_first=False,
            )
            return jsonify({
                "status": "success",
                "message": (
                    f"{date_str} の [{target_heading}] のタスクを"
                    "Googleカレンダーへ送信しました。"
                ),
                "date": date_str,
                "start_time": start_time,
                "target_heading": target_heading,
            }), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"タスクの同期処理中にエラーが発生しました: {str(e)}"
            }), 500

    @api_bp.route("/api/weather/get/today", methods=["GET"])
    def register_today_weather():
        try:
            register_today_weather_to_calendar()
            return jsonify({
                "message": "本日の天気情報をカレンダーに登録しました"
            }), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"天気情報の登録中にエラーが発生しました: {str(e)}"
            }), 500

    @api_bp.route("/api/weather/get/tomorrow", methods=["GET"])
    def register_tomorrow_weather():
        try:
            register_tomorrow_weather_to_calendar()
            return jsonify({
                "message": "翌日の天気情報をカレンダーに登録しました"
            }), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"天気情報の登録中にエラーが発生しました: {str(e)}"
            }), 500

    @api_bp.route("/api/calendar/sync-tasks/today", methods=["GET"])
    def sync_today_tasks_to_calendar():
        """本日のDaily NoteのタスクをGoogleカレンダーへ送信する"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        start_time = request.args.get("start_time", "09:00")
        return _execute_task_sync(today_str, start_time)

    @api_bp.route("/api/calendar/sync-tasks/tomorrow", methods=["GET"])
    def sync_tomorrow_tasks_to_calendar():
        """翌日のDaily NoteのタスクをGoogleカレンダーへ送信する"""
        tomorrow_str = (
            datetime.now() + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        start_time = request.args.get("start_time", "09:00")
        return _execute_task_sync(tomorrow_str, start_time)

    @api_bp.route("/api/calendar/sync-tasks/date", methods=["GET"])
    def sync_tasks_by_date_to_calendar():
        """指定日のDaily NoteのタスクをGoogleカレンダーへ送信する"""
        date_str = request.args.get("date")
        start_time = request.args.get("start_time", "09:00")

        if not date_str:
            return jsonify({
                "status": "error",
                "message": (
                    "クエリパラメータ 'date' (YYYY-MM-DD) は必須です。"
                ),
            }), 400

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "status": "error",
                "message": (
                    "無効な日付フォーマットです。"
                    "YYYY-MM-DD 形式で指定してください。"
                ),
            }), 400

        return _execute_task_sync(date_str, start_time)

    @api_bp.route("/api/calendar/sync-tasks/before-15", methods=["GET"])
    def sync_before_15_tasks_to_calendar():
        """「15時まで」のタスクをGoogleカレンダーへ送信する"""
        date_str = request.args.get(
            "date",
            datetime.now().strftime("%Y-%m-%d"),
        )
        start_time = request.args.get("start_time", "09:00")

        return _execute_task_sync(
            date_str,
            start_time,
            target_heading="15時まで",
        )

    @api_bp.route("/api/calendar/sync-tasks/before-18", methods=["GET"])
    def sync_before_18_tasks_to_calendar():
        """「18時まで」のタスクをGoogleカレンダーへ送信する"""
        date_str = request.args.get(
            "date",
            datetime.now().strftime("%Y-%m-%d"),
        )
        start_time = request.args.get("start_time", "15:00")

        return _execute_task_sync(
            date_str,
            start_time,
            target_heading="18時まで",
        )

    @api_bp.route("/api/calendar/sync-tasks/after-18", methods=["GET"])
    def sync_after_18_tasks_to_calendar():
        """「18時以降」のタスクをGoogleカレンダーへ送信する"""
        date_str = request.args.get(
            "date",
            datetime.now().strftime("%Y-%m-%d"),
        )
        start_time = request.args.get("start_time", "18:00")

        return _execute_task_sync(
            date_str,
            start_time,
            target_heading="18時以降",
        )
