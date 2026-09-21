from myutils.youtube_api.fetch_youtube_data import YouTubeAPI


def fetch_youtube_videos(query: str, max_results: int = 45) -> list:
    """YouTube Data APIを使用して動画を検索し、整形したリストを返す"""
    if not query:
        return []

    yt_api = YouTubeAPI()

    response = yt_api.search_videos(
        query=query,
        max_results=max_results,
    )

    items = []

    for item in response.get("items", []):
        if "videoId" not in item.get("id", {}):
            continue

        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        items.append({
            "id": video_id,
            "filetitle": snippet["title"],
            "dirpath": f"YouTube / {snippet['channelTitle']}",
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "type": "youtube",
        })

    return items


def fetch_youtube_video_info(video_id: str) -> dict:
    """YouTube Data APIを使用して指定動画の詳細情報を取得する"""
    yt_api = YouTubeAPI()

    item = yt_api.get_video_details_with_cache(
        video_id,
    )

    if item is None:
        return None

    snippet = item["snippet"]

    return {
        "id": video_id,
        "filetitle": snippet["title"],
        "dirpath": f"YouTube / {snippet['channelTitle']}",
        "thumbnail": snippet["thumbnails"]["high"]["url"],
        "type": "youtube",
    }
