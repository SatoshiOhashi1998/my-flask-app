import os
from googleapiclient.discovery import build

def fetch_youtube_videos(query: str, max_results: int = 45) -> list:
    """YouTube Data APIを使用して動画を検索し、整形したリストを返す"""
    if not query:
        return []

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is not set.")

    youtube = build('youtube', 'v3', developerKey=api_key)
    
    response = youtube.search().list(
        q=query,
        part='snippet',
        type='video',
        maxResults=max_results
    ).execute()

    items = []
    for item in response.get('items', []):
        if 'videoId' not in item.get('id', {}):
            continue

        video_id = item['id']['videoId']
        snippet = item['snippet']
        
        items.append({
            'id': video_id,
            'filetitle': snippet['title'],
            'dirpath': f"YouTube / {snippet['channelTitle']}",
            'thumbnail': snippet['thumbnails']['high']['url'],
            'type': 'youtube'
        })

    items = items
    return items

def fetch_youtube_video_info(video_id: str) -> dict:
    """YouTube Data APIを使用して指定動画の詳細情報を取得する"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is not set.")

    youtube = build('youtube', 'v3', developerKey=api_key)
    
    response = youtube.videos().list(
        part='snippet',
        id=video_id
    ).execute()

    items = response.get('items', [])
    if not items:
        return None

    item = items[0]
    snippet = item['snippet']

    return {
        'id': video_id,
        'filetitle': snippet['title'],
        'dirpath': f"YouTube / {snippet['channelTitle']}",
        'thumbnail': snippet['thumbnails']['high']['url'],
        'type': 'youtube'
    }