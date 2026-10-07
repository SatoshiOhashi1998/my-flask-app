import os
from datetime import datetime

from flask import request

from app.notes.vocabulary_manager import (
    export_english_vocabulary,
    export_single_vocabulary,
)
from app.notes.note_manager import (
    create_dailynote,
    create_next_weekly_note,
    add_thino_summary_to_weekly_note,
    add_comment_summary_to_weekly_note,
)

from app.utils.api_response import success, error

from myutils.markdown.vault import Vault
from myutils.markdown.note_processor import NoteGenerator


def register_markdown_routes(api_bp):
    """Markdown関連のAPIルートを登録する。"""

    @api_bp.route("/api/markdown/create_dailynote", methods=["GET"])
    def create_dailynotes():
        start_date_str = request.args.get("start_date")
        start_date = None

        if start_date_str:
            try:
                start_date = datetime.strptime(
                    start_date_str,
                    "%Y-%m-%d",
                )
            except ValueError:
                return error(
                    (
                        "無効な日付フォーマットです。"
                        "YYYY-MM-DD 形式で指定してください。"
                    ),
                    400,
                )
        else:
            start_date = datetime.now()

        try:
            create_dailynote(start_date=start_date)

            target_date_str = (
                start_date or datetime.now()
            ).strftime("%Y-%m-%d")

            return success(
                data={
                    "start_date": target_date_str,
                },
                message=(
                    f"{target_date_str} から7日分の"
                    "デイリーノートを作成しました"
                ),
            )

        except Exception as e:
            return error(
                (
                    f"デイリーノートの作成中に"
                    f"エラーが発生しました: {str(e)}"
                ),
                500,
            )

    @api_bp.route("/api/markdown/export_english", methods=["GET"])
    def export_english():
        export_english_vocabulary()

        return success(
            message="英単語を出力しました",
        )

    @api_bp.route("/api/markdown/export_vocablary", methods=["GET"])
    def export_vocablary():
        export_single_vocabulary()

        return success(
            message="語彙を出力しました",
        )

    @api_bp.route("/api/markdown/create_weekly_note", methods=["GET"])
    def create_weekly_note_endpoint():
        target_date_str = request.args.get("target_date")
        target_date = None

        if target_date_str:
            try:
                target_date = datetime.strptime(
                    target_date_str,
                    "%Y-%m-%d",
                )
            except ValueError:
                return error(
                    (
                        "無効な日付フォーマットです。"
                        "YYYY-MM-DD 形式で指定してください。"
                    ),
                    400,
                )
        else:
            target_date = datetime.now()

        output_dir = os.getenv("WEEKLY_NOTE_DIR")
        template_path = os.getenv("WEEKLY_NOTE_TEMPLATE")
        plan_dir = os.getenv("PLAN_NOTE_DIR")

        if not output_dir or not template_path:
            return error(
                (
                    "環境変数 WEEKLY_NOTE_DIR または "
                    "WEEKLY_NOTE_TEMPLATE が設定されていません。"
                ),
                500,
            )

        try:
            vault = Vault(output_dir)
            generator = NoteGenerator(vault)

            generator.create_weekly_note(
                output_dir="",
                target_date=target_date,
                template_path=template_path,
                plan_dir=plan_dir,
                start_of_week="monday",
            )

            return success(
                data={
                    "target_date": target_date.strftime("%Y-%m-%d"),
                },
                message=(
                    f"{target_date.strftime('%Y-%m-%d')} の属する週の"
                    "ウィークリーノートを作成しました"
                ),
            )

        except Exception as e:
            return error(
                (
                    f"ウィークリーノートの作成中に"
                    f"エラーが発生しました: {str(e)}"
                ),
                500,
            )

    @api_bp.route(
        "/api/markdown/create_next_weekly_note",
        methods=["GET"],
    )
    def create_next_weekly_note_endpoint():
        try:
            create_next_weekly_note()

            return success(
                message="翌週分のウィークリーノートを作成しました",
            )

        except Exception as e:
            return error(
                (
                    f"翌週のウィークリーノートの作成中に"
                    f"エラーが発生しました: {str(e)}"
                ),
                500,
            )

    @api_bp.route(
        "/api/markdown/add_thino_summary",
        methods=["GET"],
    )
    def add_thino_summary():
        try:
            add_thino_summary_to_weekly_note()

            return success(
                message="今週のThino Summaryを更新しました",
            )

        except Exception as e:
            return error(
                (
                    f"Thino Summaryの更新中に"
                    f"エラーが発生しました: {str(e)}"
                ),
                500,
            )

    @api_bp.route(
        "/api/markdown/add_thino_summary/<date_str>",
        methods=["GET"],
    )
    def add_thino_summary_by_date(date_str):
        try:
            target_date = datetime.strptime(
                date_str,
                "%Y-%m-%d",
            )

        except ValueError:
            return error(
                (
                    "無効な日付フォーマットです。"
                    "YYYY-MM-DD 形式で指定してください。"
                ),
                400,
            )

        try:
            add_thino_summary_to_weekly_note(
                target_date=target_date,
            )

            return success(
                data={
                    "target_date": date_str,
                },
                message=(
                    f"{date_str} の属する週の"
                    "Thino Summaryを更新しました"
                ),
            )

        except Exception as e:
            return error(
                (
                    f"Thino Summaryの更新中に"
                    f"エラーが発生しました: {str(e)}"
                ),
                500,
            )
