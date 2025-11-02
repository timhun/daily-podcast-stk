import os
import pickle
import googleapiclient.discovery
import googleapiclient.http
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from loguru import logger
from datetime import datetime
import json

# 配置
CLIENT_SECRETS_FILE = 'client_secrets.json'  # 從 Google Cloud 下載
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
PLAYLIST_ID = os.getenv('YOUTUBE_PLAYLIST_ID', 'YOUR_PODCAST_PLAYLIST_ID')  # 從 .env 或 config.json 讀取

def get_authenticated_service():
    """取得 YouTube API 服務實例"""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=creds)
    return youtube

def upload_to_youtube(title, description, file_path, playlist_id=PLAYLIST_ID, category_id='22', privacy_status='public'):
    """上傳影片到 YouTube"""
    try:
        youtube = get_authenticated_service()
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['podcast', 'market', 'analysis', 'finance', 'stock'],
                'categoryId': category_id  # 22 = People & Blogs
            },
            'status': {
                'privacyStatus': privacy_status
            }
        }

        media = googleapiclient.http.MediaFileUpload(file_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        response = request.execute()

        video_id = response['id']
        logger.info(f"影片上傳成功，ID: {video_id}")

        # 添加到播放清單
        if playlist_id and playlist_id != 'YOUR_PODCAST_PLAYLIST_ID':
            playlist_request = youtube.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            )
            playlist_request.execute()
            logger.info(f"影片已添加至播放清單: {playlist_id}")

        return video_id
    except Exception as e:
        logger.error(f"上傳失敗: {str(e)}")
        return None

if __name__ == "__main__":
    # 範例使用
    title = "Market Podcast - 2025-09-13"
    description = "Weekly market analysis and trends for stocks and commodities."
    file_path = "data/podcast/20250913_us.mp3"  # 您的音頻檔案路徑
    video_id = upload_to_youtube(title, description, file_path)
    if video_id:
        print(f"上傳成功！YouTube 連結: https://youtu.be/{video_id}")
