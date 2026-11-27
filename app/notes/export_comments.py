import re
import os
import unicodedata
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models import db, Comment, VideoDataModel, MusicDataModel
from app.youtube.youtube_api import fetch_youtube_video_info
from myutils.markdown.note_processor import NoteParser
from myutils.markdown.utils import MarkdownUtils
from myutils.markdown.vault import Note


JST = ZoneInfo("Asia/Tokyo")


def is_watch_date_comment(content: str) -> bool:
    """
    デフォルトの視聴日コメントかどうかを判定する。

    対象例:
        視聴日: 2026-11-27

    それ以外のコメントは通常コメントとして扱う。
    """
    if not content:
        return False

    content = content.strip()

    match = re.fullmatch(
        r"視聴日:\s*(\d{4}-\d{2}-\d{2})",
        content,
    )

    if not match:
        return False

    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_comment_media_name(comment):
    media_type = comment.media_type or "video"

    if media_type == "video":
        item = VideoDataModel.query.get(comment.video_id)

        if item:
            return item.original_name

        return comment.video_id

    elif media_type == "audio":
        item = MusicDataModel.query.get(comment.video_id)

        if item:
            return item.original_name

        return comment.video_id

    elif media_type == "youtube":
        try:
            yt_info = fetch_youtube_video_info(comment.video_id)

            if yt_info:
                return yt_info.get(
                    "filetitle",
                    comment.video_id,
                )

        except Exception as e:
            print(
                f"YouTube video info fetch error "
                f"for ID {comment.video_id}: {e}"
            )

        return comment.video_id

    return comment.video_id


def export_comments_to_md(output_dir=None, target_date=None):
    """
    指定した日のコメントを取得し、Markdownファイルとして出力する。

    呼び出し元で Flask アプリケーションコンテキスト内に
    入っている必要があります。

    Args:
        output_dir:
            Markdownファイルの出力先。
            Noneの場合は環境変数 EXPORT_DIR を使用する。

        target_date:
            出力対象の日付。
            date型またはdatetime型を指定する。

    Returns:
        str:
            出力したMarkdownファイルのパス。

    - 日付は日本時間（JST）を基準とする
    - コメントが0件でもMarkdownファイルを作成する
    - 既存のMarkdownファイルがあれば完全に上書きする
    - コメント本文は複数行・空行を含めて引用ブロックとして出力する
    - 見出しはUnicode NFC形式に正規化する
    """
    if not output_dir:
        output_dir = os.getenv("EXPORT_DIR", "./exports")

    if target_date is None:
        raise ValueError("target_dateを指定してください。")

    if isinstance(target_date, datetime):
        target_date = target_date.date()

    if not isinstance(target_date, date):
        raise TypeError(
            "target_dateはdate型またはdatetime型で指定してください。"
        )

    os.makedirs(output_dir, exist_ok=True)

    start_dt = datetime.combine(
        target_date,
        time.min,
        tzinfo=JST,
    )
    end_dt = start_dt + timedelta(days=1)

    comments = (
        Comment.query
        .filter(
            Comment.created_at >= start_dt,
            Comment.created_at < end_dt,
        )
        .order_by(Comment.created_at.asc())
        .all()
    )

    if not comments:
        print(f"{target_date.isoformat()}のコメントはありません。")

    filename = f"comments_{target_date.isoformat()}.md"
    file_path = os.path.join(output_dir, filename)

    md_lines = [
        "---",
        f"created: {target_date.isoformat()}",
        "---",
        "",
        f"# 本日のコメントまとめ ({target_date.isoformat()})",
        "",
        f"合計コメント数: **{len(comments)}件**",
        "",
    ]

    
    # コメントを視聴記録と通常コメントに分類
    watch_comments = [
        c for c in comments
        if is_watch_date_comment(c.content)
    ]

    normal_comments = [
        c for c in comments
        if not is_watch_date_comment(c.content)
    ]

    # コメント1件分のMarkdown出力
    def append_comment(c):
        time_str = c.created_at.strftime("%H:%M:%S")
        media_type = c.media_type or "video"

        # メディア名を取得
        media_name = get_comment_media_name(c)

        # 見出しをUnicode NFC形式に正規化
        media_name = unicodedata.normalize(
            "NFC",
            media_name,
        )

        watch_url = (
            f"http://localhost:5000/react/MediaPlayer/watch"
            f"?v={c.video_id}&type={media_type}"
        )

        quoted_content = "\n".join(
            f"> {line}"
            for line in c.content.splitlines()
        )

        md_lines.append(f"### {media_name}")
        md_lines.append(
            f"- **URL**: [{watch_url}]({watch_url})"
        )
        md_lines.append(f"- **時間**: {time_str}")
        md_lines.append("- **内容**:")
        md_lines.append(quoted_content)
        md_lines.append("")

    # 視聴記録を出力
    md_lines.append("## 視聴記録")
    md_lines.append("")

    for c in watch_comments:
        append_comment(c)

    # 通常コメントを出力
    md_lines.append("## 通常コメント")
    md_lines.append("")

    for c in normal_comments:
        append_comment(c)


    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Markdownを出力しました: {file_path}")

    return file_path


def export_today_comments_to_md(output_dir=None, now=None):
    """
    本日のコメントを取得し、Markdownファイルとして出力する。

    内部ではexport_comments_to_md()を使用する。

    Args:
        output_dir:
            Markdownファイルの出力先。
            Noneの場合は環境変数 EXPORT_DIR を使用する。

        now:
            現在日時。
            テスト時などに指定可能。
            Noneの場合は現在のJSTを使用する。

    Returns:
        export_comments_to_md()の戻り値。
    """
    if now is None:
        now = datetime.now(JST)

    return export_comments_to_md(
        output_dir=output_dir,
        target_date=now.date(),
    )


def collect_comment_links(
    comment_export_dir: str,
    target_date: datetime,
    start_of_week: str = "monday",
) -> list[str]:
    """
    指定した週のコメントMarkdownファイルから、
    各コメントの見出しへのObsidianリンクを取得する。

    対象ファイル:
        comments_YYYY-MM-DD.md

    対象となるのはMarkdown内の##見出しのみ。
    """

    if start_of_week not in ("monday", "sunday"):
        raise ValueError(
            "start_of_weekは'monday'または'sunday'を指定してください。"
        )

    start_date, end_date, _, _ = MarkdownUtils.calculate_week_range(
        target_date,
        start_of_week=start_of_week,
    )

    links = []

    current_date = start_date.date()

    while current_date <= end_date.date():
        file_name = f"comments_{current_date:%Y-%m-%d}.md"
        file_path = os.path.join(
            comment_export_dir,
            file_name,
        )

        if os.path.exists(file_path):
            note = Note(file_path)
            parser = NoteParser(note)

            headings = parser.get_headings()

            for heading in headings:
                if heading["level"] != 2:
                    continue

                heading_text = heading["text"].strip()

                if not heading_text:
                    continue

                links.append(
                    f"[[{file_name[:-3]}#{heading_text}]]"
                )

        current_date += timedelta(days=1)

    return links
