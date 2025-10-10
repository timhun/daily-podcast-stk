import os
import torch
from loguru import logger
from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()

def generate_audio(text_path, output_path):
    """Generate audio from text using Coqui TTS and apply post-processing."""
    
    # 讀取文字檔案
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"讀取文字檔案成功，字數: {len(text)}")
    except Exception as e:
        logger.error(f"無法讀取文字檔案 {text_path}: {str(e)}")
        raise

    # 使用 Coqui TTS 生成音頻
    try:
        from TTS.api import TTS
        
        logger.info("正在載入 Coqui TTS 模型...")
        
        # 使用支援中文的多語言模型
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        
        temp_path = output_path + ".tmp.wav"
        
        # 生成語音（XTTS v2 支援多語言包括中文）
        tts.tts_to_file(
            text=text,
            file_path=temp_path,
            language="zh-cn"  # 中文
        )
        
        logger.info(f"成功使用 Coqui TTS 生成音頻: {output_path}")
        
    except ImportError:
        logger.error("Coqui TTS 未安裝，請執行: pip install TTS")
        raise
    except Exception as e:
        logger.error(f"TTS 生成失敗: {str(e)}")
        raise

    # 後製處理：音量正常化、設置取樣率和位元率
    try:
        audio_segment = AudioSegment.from_wav(temp_path)
        audio_segment = audio_segment.normalize()
        audio_segment = audio_segment.set_frame_rate(44100).set_channels(2)
        audio_segment.export(output_path, format="mp3", bitrate="128k")
        logger.info(f"音頻後製完成: {output_path}")

        # 刪除臨時檔案
        os.remove(temp_path)
    except Exception as e:
        logger.error(f"音頻後製失敗: {str(e)}")
        raise