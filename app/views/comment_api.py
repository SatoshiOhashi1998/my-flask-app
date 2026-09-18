from flask import jsonify, request
from datetime import datetime

from app.models import Comment, db
from app.notes.export_comments import export_comments_to_md, export_today_comments_to_md


def register_comment_routes(api_bp):
    """コメント関連のAPIルートを登録する。"""

    @api_bp.route("/api/comments/<video_id>", methods=["GET"])
    def get_comments(video_id):
        media_type = request.args.get("type", "video")

        comments = (
            Comment.query
            .filter_by(
                video_id=video_id,
                media_type=media_type,
            )
            .order_by(Comment.created_at.desc())
            .all()
        )

        return jsonify([
            {
                "id": comment.id,
                "video_id": comment.video_id,
                "media_type": comment.media_type,
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
            }
            for comment in comments
        ])

    @api_bp.route("/api/comments/<video_id>", methods=["POST"])
    def create_comment(video_id):
        data = request.get_json()

        comment = Comment(
            video_id=video_id,
            media_type=data["media_type"],
            content=data["content"],
        )

        db.session.add(comment)
        db.session.commit()

        return jsonify({
            "message": "コメントを投稿しました",
        }), 201

    @api_bp.route("/api/comments/<int:comment_id>", methods=["PUT"])
    def update_comment(comment_id):
        comment = Comment.query.get(comment_id)

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        data = request.get_json()

        comment.content = data["content"]

        db.session.commit()

        return jsonify({
            "id": comment.id,
            "video_id": comment.video_id,
            "media_type": comment.media_type,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
        })

    @api_bp.route("/api/comments/<int:comment_id>", methods=["DELETE"])
    def delete_comment(comment_id):
        comment = Comment.query.get(comment_id)

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        db.session.delete(comment)
        db.session.commit()

        return jsonify({
            "message": "コメントを削除しました"
        })

    @api_bp.route("/api/comments/<video_id>/others", methods=["GET"])
    def get_other_comments(video_id):
        exclude_type = request.args.get(
            "exclude_type",
            "youtube",
        )

        comments = (
            Comment.query
            .filter(
                Comment.video_id == video_id,
                Comment.media_type != exclude_type,
            )
            .order_by(Comment.created_at.desc())
            .all()
        )

        return jsonify([
            {
                "id": comment.id,
                "video_id": comment.video_id,
                "media_type": comment.media_type,
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
            }
            for comment in comments
        ])

    @api_bp.route("/api/comments/export", methods=["GET"])
    def export_comments():
        export_today_comments_to_md()

        return jsonify({
            "message": "本日のコメントを出力しました"
        })

    @api_bp.route("/api/comments/export/<date_str>", methods=["GET"])
    def export_comments_by_date(date_str):
        try:
            target_date = datetime.strptime(
                date_str,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            return jsonify({
                "error": "日付はYYYY-MM-DD形式で指定してください"
            }), 400

        file_path = export_comments_to_md(
            target_date=target_date,
        )

        if file_path is None:
            return jsonify({
                "message": f"{date_str}のコメントはありません"
            }), 404

        return jsonify({
            "message": "コメントを出力しました",
            "date": date_str,
            "file_path": file_path,
        })
            