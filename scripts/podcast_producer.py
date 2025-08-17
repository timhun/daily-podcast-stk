import os
from datetime import datetime
import logging
import subprocess

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置 TTS 工具（使用 gTTS 作為示例，可替換）
TTS_COMMAND = "gtts-cli --output {output_path} --lang zh-tw {text_file}"
FALLBACK_TTS_COMMAND = "gtts-cli --output {output_path} --lang en {text_file}"

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

def generate_audio(text, output_path):
    """使用 TTS 工具生成 MP3"""
    try:
        command = TTS_COMMAND.format(output_path=output_path, text_file=text)
        subprocess.run(command, shell=True, check=True, text=True)
        logger.info(f"成功生成音檔: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"TTS 生成失敗，嘗試備用語音: {e}")
        fallback_command = FALLBACK_TTS_COMMAND.format(output_path=output_path, text_file=text)
        try:
            subprocess.run(fallback_command, shell=True, check=True, text=True)
            logger.info(f"使用備用語音生成音檔: {output_path}")
        except Exception as e:
            logger.error(f"備用 TTS 失敗: {e}")
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
        if generate_audio(text, output_path):
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
