import os
from datetime import datetime
import logging
import asyncio
import edge_tts

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置 edge-tts 參數
VOICE = "zh-TW-YunJheNeural"  # 台灣中文語音選項
FALLBACK_VOICE = "en-US-JennyNeural"  # 備用英文語音
RATE = "+0%"  # 語速調整
VOLUME = "+0%"  # 音量調整

def load_script(mode):
    """載入文字稿"""
    date_str = datetime.now().strftime("%Y%m%d")
    script_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    script_path = os.path.join(script_dir, 'script.txt')
    if not os.path.exists(script_path):
        logger.error(f"缺少文字稿: {script_path}")
        return None
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"載入文字稿失敗: {e}")
        return None

async def generate_audio(text, output_path, voice):
    """使用 edge-tts 生成 MP3"""
    try:
        communicate = edge_tts.Communicate(text, voice, rate=RATE, volume=VOLUME)
        await communicate.save(output_path)
        logger.info(f"成功生成音檔: {output_path}")
    except Exception as e:
        logger.error(f"edge-tts 生成失敗: {e}")
        return False
    return True

def save_audio(mode):
    """保存生成的 MP3 音檔"""
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'audio.mp3')
    text = load_script(mode)
    if text:
        loop = asyncio.get_event_loop()
        if mode == 'tw':
            success = loop.run_until_complete(generate_audio(text, output_path, VOICE))
        else:  # 備用英文語音
            success = loop.run_until_complete(generate_audio(text, output_path, FALLBACK_VOICE))
        if success:
            file_size = os.path.getsize(output_path)
            logger.info(f"音檔大小: {file_size} 位元組")
        else:
            logger.error(f"音檔生成失敗，跳過保存")
    else:
        logger.warning(f"無有效文字稿，跳過 {mode} 音檔生成")

def main():
    """主函數，執行播報員任務"""
    current_hour = datetime.now().hour
    if current_hour == 6:  # 6am 美股
        save_audio('us')
    elif current_hour == 14:  # 2pm 台股
        save_audio('tw')
    else:
        logger.info(f"當前時間 {current_hour}:00 CST 不在播報時段，跳過")

if __name__ == '__main__':
    main()
