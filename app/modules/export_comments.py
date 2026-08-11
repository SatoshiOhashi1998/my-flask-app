import os
from datetime import datetime, time
from app.models import db, Comment, VideoDataModel, MusicDataModel
from app.modules.youtube_api import fetch_youtube_video_info


def export_today_comments_to_md(output_dir=None):
    """
    本日のコメントを取得し、Markdownファイルとして出力します。
    呼び出し元で Flask アプリケーションコンテキスト内に入っている必要があります。
    """
    if not output_dir:
        output_dir = os.getenv('EXPORT_DIR', './exports')

    os.makedirs(output_dir, exist_ok=True)
    
    today = datetime.utcnow().date()
    start_dt = datetime.combine(today, time.min)
    end_dt = datetime.combine(today, time.max)
    
    # 本日のコメントを取得
    comments = Comment.query.filter(
        Comment.created_at >= start_dt,
        Comment.created_at <= end_dt
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
        time_str = c.created_at.strftime('%H:%M:%S')
        media_type = c.media_type or "video"
        
        if media_type == "video":
            display_type = "動画"
            item = VideoDataModel.query.get(c.video_id)
            media_name = item.original_name if item else c.video_id
        elif media_type == "audio":
            display_type = "音声"
            item = MusicDataModel.query.get(c.video_id)
            media_name = item.original_name if item else c.video_id
        else:
            display_type = "YouTube"
            media_name = "YouTube動画"
            try:
                yt_info = fetch_youtube_video_info(c.video_id)
                if yt_info:
                    media_name = yt_info.get('filetitle', c.video_id)
            except Exception as e:
                print(f"YouTube API fetch error for ID {c.video_id}: {e}")

        watch_url = f"http://localhost:5173/watch?v={c.video_id}&type={media_type}"

        md_lines.append(f"## {media_name}")
        md_lines.append(f"- **URL**: [{watch_url}]({watch_url})")
        md_lines.append(f"- **時間**: {time_str}")
        md_lines.append(f"- **内容**:")
        md_lines.append(f"> {c.content}")
        md_lines.append("")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
        
    print(f"Markdownを出力しました: {file_path}")
    return file_path
