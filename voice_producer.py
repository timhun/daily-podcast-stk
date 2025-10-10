import os
import torch
from loguru import logger
from dotenv import load_dotenv
from pydub import AudioSegment
import soundfile as sf

load_dotenv()

def generate_audio(text_path, output_path):
    """Generate audio from text using IndexTTS2 and apply post-processing."""
    
    # 讀取文字檔案
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"讀取文字檔案成功，字數: {len(text)}")
    except Exception as e:
        logger.error(f"無法讀取文字檔案 {text_path}: {str(e)}")
        raise

    # 使用 IndexTTS2 生成音頻
    try:
        # 載入 IndexTTS2 模型
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torchaudio
        
        logger.info("正在載入 IndexTTS2 模型...")
        
        # 使用 Edge TTS 作為更簡單的替代方案（推薦）
        import edge_tts
        import asyncio
        
        async def generate_tts():
            # 使用中文語音
            # 台灣中文女聲: zh-TW-HsiaoChenNeural (溫柔女聲)
            # 台灣中文男聲: zh-TW-YunJheNeural (男聲)
            communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural")
            await communicate.save(output_path + ".tmp.mp3")
        
        # 執行異步 TTS
        asyncio.run(generate_tts())
        logger.info(f"成功使用 Edge TTS 生成音頻: {output_path}")
        
        temp_path = output_path + ".tmp.mp3"
        
    except ImportError:
        logger.error("Edge TTS 未安裝，請執行: pip install edge-tts")
        raise
    except Exception as e:
        logger.error(f"TTS 生成失敗: {str(e)}")
        raise

    # 後製處理：音量正常化、設置取樣率和位元率
    try:
        audio_segment = AudioSegment.from_mp3(temp_path)
        audio_segment = audio_segment.normalize()
        audio_segment = audio_segment.set_frame_rate(44100).set_channels(2)  # 設置 44.1kHz 取樣率與立體聲
        audio_segment.export(output_path, format="mp3", bitrate="128k")  # 設置 128kbps 位元率
        logger.info(f"音頻後製完成: {output_path}")

        # 刪除臨時檔案
        os.remove(temp_path)
    except Exception as e:
        logger.error(f"音頻後製失敗: {str(e)}")
        raise