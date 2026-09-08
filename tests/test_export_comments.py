import unicodedata
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models import db, Comment, VideoDataModel, MusicDataModel
from app.modules.export_comments import export_today_comments_to_md


class TestExportTodayCommentsToMd:

    def test_export_no_comments(self, app):
        """本日のコメントがない場合、ファイルを作成せずNoneを返す。"""
        with app.app_context():
            result = export_today_comments_to_md()

            assert result is None

    def test_export_multiline_comment(self, app, tmp_path):
        """複数行・空行を含むコメントが正しく引用ブロックになる。"""
        with app.app_context():
            comment = Comment(
                video_id="test-video",
                media_type="video",
                content="1行目\n2行目\n\n4行目",
                created_at=datetime(2026, 9, 8, 12, 0, 0),
            )
            db.session.add(comment)
            db.session.commit()

            video = VideoDataModel(
                # 実際のモデルに必要なフィールドを追加してください
                id="test-video",
                original_name="テスト動画",
            )
            db.session.add(video)
            db.session.commit()

            result = export_today_comments_to_md(
                output_dir=tmp_path
            )

            assert result is not None

            content = Path(result).read_text(encoding="utf-8")

            assert "> 1行目" in content
            assert "> 2行目" in content
            assert "> " in content
            assert "> 4行目" in content

    def test_heading_is_normalized_to_nfc(self, app, tmp_path):
        """見出しがUnicode NFC形式に正規化される。"""
        with app.app_context():
            # NFD形式の文字列を作る
            media_name = unicodedata.normalize(
                "NFD",
                "なぜ日本語なのか"
            )

            comment = Comment(
                video_id="test-video",
                media_type="video",
                content="テストコメント",
                created_at=datetime(2026, 9, 8, 12, 0, 0),
            )
            db.session.add(comment)
            db.session.commit()

            video = VideoDataModel(
                id="test-video",
                original_name=media_name,
            )
            db.session.add(video)
            db.session.commit()

            result = export_today_comments_to_md(
                output_dir=tmp_path
            )

            content = Path(result).read_text(encoding="utf-8")

            # Markdownの見出しを取得
            heading = next(
                line
                for line in content.splitlines()
                if line.startswith("## ")
            )

            heading_text = heading[3:]

            assert heading_text == unicodedata.normalize(
                "NFC",
                media_name
            )

            assert unicodedata.is_normalized(
                "NFC",
                heading_text
            )

    def test_existing_file_is_overwritten(self, app, tmp_path):
        """既存のMarkdownファイルが完全に上書きされる。"""
        with app.app_context():
            old_file = (
                tmp_path /
                "comments_2026-09-08.md"
            )

            old_file.write_text(
                "古い内容\n削除されるべき内容",
                encoding="utf-8"
            )

            comment = Comment(
                video_id="test-video",
                media_type="video",
                content="新しいコメント",
                created_at=datetime(2026, 9, 8, 12, 0, 0),
            )
            db.session.add(comment)
            db.session.commit()

            video = VideoDataModel(
                id="test-video",
                original_name="テスト動画",
            )
            db.session.add(video)
            db.session.commit()

            result = export_today_comments_to_md(
                output_dir=tmp_path
            )

            content = Path(result).read_text(
                encoding="utf-8"
            )

            assert "新しいコメント" in content
            assert "古い内容" not in content
            assert "削除されるべき内容" not in content

    def test_jst_date_boundary(self, app, tmp_path):
        """日本時間の日付を基準にコメントが抽出される。"""
        with app.app_context():
            comment = Comment(
                video_id="test-video",
                media_type="video",
                content="JSTテスト",
                created_at=datetime(2026, 9, 8, 0, 30),
            )
            db.session.add(comment)
            db.session.commit()

            video = VideoDataModel(
                id="test-video",
                original_name="テスト動画",
            )
            db.session.add(video)
            db.session.commit()

            result = export_today_comments_to_md(
                output_dir=tmp_path,
                now=datetime(
                    2026, 9, 8, 1, 0,
                )
            )

            content = Path(result).read_text(
                encoding="utf-8"
            )

            assert "JSTテスト" in content
            assert "comments_2026-09-08.md" in str(result)
