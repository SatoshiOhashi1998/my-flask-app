import traceback

from flask import jsonify, request

from devtools.use_clip_board import copy_code


def register_clipboard_routes(api_bp):
    @api_bp.route("/api/clipboard/copy-code", methods=["GET", "POST"])
    def copy_code_endpoint():

        if request.method == "GET":
            target = request.args.get("target")

            if not target:
                return jsonify({
                    "status": "error",
                    "message": "target は必須です。"
                }), 400

            extensions = request.args.getlist("extension")
            if not extensions:
                extensions = None

            exclude_dirs = request.args.getlist("exclude_dir")
            if not exclude_dirs:
                exclude_dirs = None

            recursive = request.args.get(
                "recursive",
                default="true",
            ).lower() == "true"

        else:
            data = request.get_json(silent=True) or {}

            target = data.get("target")

            if not target:
                return jsonify({
                    "status": "error",
                    "message": "target は必須です。"
                }), 400

            extensions = (
                set(data["extensions"])
                if data.get("extensions")
                else None
            )

            exclude_dirs = (
                set(data["exclude_dirs"])
                if data.get("exclude_dirs")
                else None
            )

            recursive = data.get(
                "recursive",
                True,
            )

        try:
            files = copy_code(
                target=target,
                extensions=extensions,
                exclude_dirs=exclude_dirs,
                recursive=recursive,
            )

            return jsonify({
                "status": "success",
                "message": (
                    f"{len(files)} ファイルを"
                    "クリップボードへコピーしました。"
                ),
                "files": [str(path) for path in files],
            }), 200

        except Exception as e:
            traceback.print_exc()

            return jsonify({
                "status": "error",
                "message": (
                    f"コードのコピー中にエラーが発生しました: {str(e)}"
                ),
            }), 500
