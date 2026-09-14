import os
import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models import db, Comment, VideoDataModel, MusicDataModel
from app.modules.youtube_api import fetch_youtube_video_info


JST = ZoneInfo("Asia/Tokyo")


def export_today_comments_to_md(output_dir=None, now=None):
    """
    本日のコメントを取得し、Markdownファイルとして出力します。
    呼び出し元で Flask アプリケーションコンテキスト内に入っている必要があります。

    - 日付は日本時間（JST）を基準とする
    - 既存のMarkdownファイルがあれば完全に上書きする
    - コメント本文は複数行・空行を含めて引用ブロックとして出力する
    - 見出しはUnicode NFC形式に正規化する
    """
    if not output_dir:
        output_dir = os.getenv("EXPORT_DIR", "./exports")

    if now is None:
        now = datetime.now(JST)

    today = now.date()

    os.makedirs(output_dir, exist_ok=True)

    start_dt = datetime.combine(
        today,
        time.min,
        tzinfo=JST
    )
    end_dt = start_dt + timedelta(days=1)

    # 本日のコメントを取得
    comments = Comment.query.filter(
        Comment.created_at >= start_dt,
        Comment.created_at < end_dt
    ).order_by(Comment.created_at.asc()).all()

    if not comments:
        print("本日のコメントはありません。")
        return None

    filename = f"comments_{today.isoformat()}.md"
    file_path = os.path.join(output_dir, filename)

    md_lines = [
        "---",
        f"created: {today.isoformat()}",
        "---",
        "",
        f"# 本日のコメントまとめ ({today.isoformat()})",
        "",
        f"合計コメント数: **{len(comments)}件**",
        ""
    ]

    for c in comments:
        time_str = c.created_at.strftime("%H:%M:%S")
        media_type = c.media_type or "video"

        if media_type == "video":
            item = VideoDataModel.query.get(c.video_id)
            media_name = item.original_name if item else c.video_id

        elif media_type == "audio":
            item = MusicDataModel.query.get(c.video_id)
            media_name = item.original_name if item else c.video_id

        else:
            media_name = "YouTube動画"

            try:
                yt_info = fetch_youtube_video_info(c.video_id)

                if yt_info:
                    media_name = yt_info.get(
                        "filetitle",
                        c.video_id
                    )

            except Exception as e:
                print(
                    f"YouTube API fetch error for ID "
                    f"{c.video_id}: {e}"
                )

        # Obsidianの見出しリンクとのUnicode表現を統一
        media_name = unicodedata.normalize("NFC", media_name)

        watch_url = (
            f"http://localhost:5173/watch"
            f"?v={c.video_id}&type={media_type}"
        )

        # コメント本文の各行をMarkdownの引用にする。
        # 空行にも "> " を付けることで、
        # 複数段落でも1つの引用ブロックとして維持する。
        quoted_content = "\n".join(
            f"> {line}"
            for line in c.content.splitlines()
        )

        md_lines.append(f"## {media_name}")
        md_lines.append(
            f"- **URL**: [{watch_url}]({watch_url})"
        )
        md_lines.append(f"- **時間**: {time_str}")
        md_lines.append("- **内容**:")
        md_lines.append(quoted_content)
        md_lines.append("")

    # 既存ファイルがあっても完全に上書きする
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Markdownを出力しました: {file_path}")

    return file_path
