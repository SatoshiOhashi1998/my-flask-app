from datetime import datetime

from flask import jsonify, request

from app.notes.note_manager import add_comment_summary_to_weekly_note


def register_test_routes(api_bp):

    @api_bp.route("/test", methods=["GET"])
    def test():
        return jsonify({
            "message": "test endpoint",
            "status": "ok",
        })

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

            return jsonify({
                "status": "success",
                "message": "Comment SummaryをWeekly Noteに追加しました。",
                "date": (
                    target_date.strftime("%Y-%m-%d")
                    if target_date
                    else datetime.now().strftime("%Y-%m-%d")
                ),
            })

        except ValueError as e:
            return jsonify({
                "status": "error",
                "message": str(e),
            }), 400

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
            }), 500
