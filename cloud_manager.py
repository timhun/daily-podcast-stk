from b2sdk.v2 import InMemoryAccountInfo, B2Api
import os
import json
from loguru import logger
import httpx

logger.add("logs/cloud_manager.log", rotation="1 MB")

def upload_episode(date, mode, files):
    """
    上傳 podcast 音頻和腳本至 B2。
    如果 B2 認證失敗 (bad_auth_token / 401 / network):
       - 改用本地 absolute path (local:// scheme)
       - Podcast 仍可在本地播放，但 RSS 無法提供有效的 CDN URL
    """
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", os.getenv("B2_KEY_ID"), os.getenv("B2_APPLICATION_KEY"))
        bucket = b2_api.get_bucket_by_name(os.getenv("B2_BUCKET_NAME"))
    except Exception as e:
        logger.error(f"B2 初始化失敗: {e} → 降級到本地路徑")
        uploaded = {}
        for file_type, file_path in files.items():
            abs_path = os.path.abspath(file_path)
            uploaded[file_type] = f"local://{abs_path}"
            logger.warning(f"  {file_type}: {uploaded[file_type]}")
        return uploaded

    uploaded = {}
    for file_type, file_path in files.items():
        file_name = os.path.basename(file_path)
        try:
            bucket.upload_local_file(local_file=file_path, file_name=file_name)
            uploaded[file_type] = f"https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/{file_name}"
            logger.info(f"✅ B2 上傳: {file_type} → {file_name}")
        except Exception as e:
            logger.error(f"⚠️ B2 上傳失敗 {file_type} ({e.__class__.__name__}): {e}")
            # Graceful fallback → 本地 path
            abs_path = os.path.abspath(file_path)
            uploaded[file_type] = f"local://{abs_path}"
            logger.warning(f"  {file_type} 降級到本地: {abs_path}")
    return uploaded

def upload_rss(rss_path):
    """
    上傳 podcast.xml RSS feed 至 B2。
    如果認證失敗，回傳 local:// URI 以避免崩潰。
    """
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", os.getenv("B2_KEY_ID"), os.getenv("B2_APPLICATION_KEY"))
        bucket = b2_api.get_bucket_by_name(os.getenv("B2_BUCKET_NAME"))
        b2_file_name = "podcast.xml"
        bucket.upload_local_file(local_file=rss_path, file_name=b2_file_name)
        rss_url = f"https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/{b2_file_name}"
        logger.info(f"✅ B2 RSS 上傳: {rss_url}")
        return rss_url
    except Exception as e:
        logger.error(f"⚠️ B2 RSS 上傳失敗 ({e.__class__.__name__}): {e}")
        abs_path = os.path.abspath(rss_path)
        local_url = f"local://{abs_path}"
        logger.warning(f"  RSS 降級到本地: {local_url}")
        return local_url

def upload_chart(local_file_path):
    """
    上傳策略績效圖表至 B2。
    如果認證失敗，回傳 None（不阻斷流程）。
    圖表 URL 主要用於 Slack 通知中的可點擊連結。
    """
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", os.getenv("B2_KEY_ID"), os.getenv("B2_APPLICATION_KEY"))
        bucket = b2_api.get_bucket_by_name(os.getenv("B2_BUCKET_NAME"))
        file_name = os.path.basename(local_file_path)
        b2_file_name = f"charts/{file_name}"
        bucket.upload_local_file(local_file=local_file_path, file_name=b2_file_name)
        chart_url = f"https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/{b2_file_name}"
        logger.info(f"✅ B2 圖表上傳: {chart_url}")
        return chart_url
    except Exception as e:
        logger.error(f"⚠️ B2 圖表上傳失敗 ({e.__class__.__name__}): {e}")
        return None  # 不阻斷策略流程
