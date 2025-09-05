import os
import torch
from transformers import pipeline
from pydub import AudioSegment
from loguru import logger
import json

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 配置日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

def generate_audio(text_path, output_path, model_name="microsoft/VibeVoice-1.5B"):
    """
    使用 VibeVoice 生成語音，並進行後處理以符合 podcast 平台需求。
    
    Args:
        text_path (str): 輸入文字稿路徑
        output_path (str): 輸出音頻檔案路徑
        model_name (str): VibeVoice 模型名稱，預設為 1.5B
    """
    try:
        # 讀取文字稿
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        # 確保文字稿在 VibeVoice 的長度限制內（約 3000 字，假設每字約 1 秒）
        if len(text) > config['podcast']['script_length_limit']:
            logger.warning(f"文字稿長度 {len(text)} 超過限制 {config['podcast']['script_length_limit']}，將截斷")
            text = text[:config['podcast']['script_length_limit']]
        
        # 初始化 VibeVoice 模型
        logger.info(f"正在載入 VibeVoice 模型: {model_name}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts_pipeline = pipeline("text-to-speech", model=model_name, device=device)
        
        # 設置講者與語音參數（假設單講者，使用預設中文聲音）
        speaker_id = "zh_speaker_1"  # VibeVoice 支援多講者，需指定 ID（需根據模型文件確認）
        tts_config = {
            "language": "zh",  # 繁體中文
            "speaker_id": speaker_id,
            "sample_rate": 24000,  # VibeVoice 預設 24kHz，稍後轉換為 44.1kHz
            "rate": 1.1,  # 語速加快 10%（對應 edge_tts 的 +10%）
            "pitch": 0.0  # 音調不變（對應 edge_tts 的 +0Hz）
        }
        
        # 生成語音
        logger.info(f"生成語音，輸入文字長度: {len(text)}")
        audio_data = tts_pipeline(text, **tts_config)
        
        # 保存初始音頻（假設 VibeVoice 輸出為 WAV 格式）
        temp_output = output_path.replace(".mp3", "_temp.wav")
        with open(temp_output, "wb") as f:
            f.write(audio_data["audio"])
        
        # 後處理：正規化、轉換格式
        audio = AudioSegment.from_wav(temp_output)
        audio = audio.normalize()  # 音量正規化
        audio = audio.set_frame_rate(44100).set_channels(2)  # 設置 44.1kHz 立體聲
        audio.export(output_path, format="mp3", bitrate="128k")  # 轉為 128kbps MP3
        
        # 清理臨時檔案
        os.remove(temp_output)
        
        logger.info(f"語音生成完成，儲存至: {output_path}")
        
    except Exception as e:
        logger.error(f"語音生成失敗: {str(e)}")
        raise
    
if __name__ == "__main__":
    # 測試範例
    test_text_path = f"{config['data_paths']['podcast']}/test_script.txt"
    test_output_path = f"{config['data_paths']['podcast']}/test_output.mp3"
    os.makedirs(os.path.dirname(test_output_path), exist_ok=True)
    with open(test_text_path, 'w', encoding='utf-8') as f:
        f.write("歡迎收聽《幫幫忙說AI投資》，這是測試語音。")
    generate_audio(test_text_path, test_output_path)
