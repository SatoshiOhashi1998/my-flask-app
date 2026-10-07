from datetime import datetime

from flask import request

from app.notes.note_manager import add_comment_summary_to_weekly_note
from app.utils.api_response import success, error


def register_test_routes(api_bp):

    @api_bp.route("/test", methods=["GET"])
    def test():

        return success(
            message="test endpoint",
        )

    @api_bp.route("/test/add-comment-summary", methods=["GET"])
    def test_add_comment_summary():
        try:
            # ?date=2026-09-15
            date_str = request.args.get("date")

            if date_str:
                target_date = datetime.strptime(
                    date_str,
                    "%Y-%m-%d",
                )
            else:
                target_date = None

            add_comment_summary_to_weekly_note(
                target_date=target_date,
                start_of_week="monday",
            )

            return success(
                data={
                    "date": (
                        target_date.strftime("%Y-%m-%d")
                        if target_date
                        else datetime.now().strftime("%Y-%m-%d")
                    ),
                },
                message="Comment SummaryをWeekly Noteに追加しました。",
            )

        except ValueError as e:
            return error(str(e), 400)

        except Exception as e:
            return error(str(e), 500)
