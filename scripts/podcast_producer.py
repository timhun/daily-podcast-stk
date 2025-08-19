#podcast_producer.py
import os
import json
from datetime import datetime
import logging
import asyncio
from edge_tts import Communicate

# 設定日誌
logging.basicConfig(filename='logs/podcast_producer.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(mode='tw'):
    """載入 config.json 配置文件"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        voices = config.get('voices', {'tw': 'zh-TW-YunJheNeural', 'us': 'zh-TW-YunJheNeural'})
        return voices.get(mode, voices.get('tw')), config.get('rate', '+0%'), config.get('volume', '+0%')
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def load_script(mode='tw'):
    """載入文字稿"""
    date_str = datetime.now().strftime("%Y%m%d")
    script_path = os.path.join('docs', 'podcast', f"{date_str}_{mode}", 'script.txt')
    if not os.path.exists(script_path):
        logger.error(f"缺少文字稿: {script_path}")
        raise FileNotFoundError(f"缺少文字稿: {script_path}")
    with open(script_path, 'r', encoding='utf-8') as f:
        script = f.read()
    logger.info(f"載入文字稿: {script_path}, 長度 {len(script)} 字元")
    return script

async def generate_audio(script, voice, rate, volume, output_path):
    """使用 edge-tts 生成語音並保存為 MP3"""
    try:
        communicate = Communicate(script, voice=voice, rate=rate, volume=volume)
        await communicate.save(output_path)
        file_size = os.path.getsize(output_path) / 1024  # KB
        logger.info(f"語音生成完成: {output_path}, 大小 {file_size:.2f} KB, 參數 - 語音: {voice}, 速度: {rate}, 音量: {volume}")
    except Exception as e:
        logger.error(f"語音生成失敗: {e}")
        raise

def get_output_path(mode='tw'):
    """生成並返回 MP3 檔案路徑"""
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, 'audio.mp3')

def main(mode='tw'):
    """主函數，執行播報生成"""
    voice, rate, volume = load_config(mode)
    script = load_script(mode)
    output_path = get_output_path(mode)
    asyncio.run(generate_audio(script, voice, rate, volume, output_path))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='播報員腳本')
    parser.add_argument('--mode', default='tw', choices=['tw', 'us'], help='播客模式 (tw/us)')
    args = parser.parse_args()
    main(args.mode)
