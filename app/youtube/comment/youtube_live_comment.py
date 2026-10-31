from youtube_live_chat_collector import run_current


def run_youtube_live_comment() -> None:
    stats = run_current()

    print("\n=== PersonalHub: YouTube Sync ===")
    print(f"対象チャンネル数: {stats['total']}")
    print(f"成功: {stats['completed']}")
    print(f"失敗: {stats['failed']}")


if __name__ == "__main__":
    run_youtube_live_comment()
