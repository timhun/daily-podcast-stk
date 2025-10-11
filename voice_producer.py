import os
import asyncio
from loguru import logger
from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()

def generate_audio_elevenlabs(text, output_path):
    """使用 ElevenLabs 生成音頻（方案1）"""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("ELEVENLABS_API_KEY 未設置")
        return False
    
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import save
        
        VOICE_IDS = {
            "adam": "pNInz6obpgDQGcFmaJgB",
        }
        
        client = ElevenLabs(api_key=api_key)
        voice_id = VOICE_IDS["adam"]
        
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_turbo_v2"
        )
        
        temp_path = output_path + ".tmp.mp3"
        save(audio, temp_path)
        
        logger.info("✓ 成功使用 ElevenLabs 生成音頻")
        return temp_path
        
    except ImportError as e:
        logger.warning(f"ElevenLabs 導入失敗: {e}")
        return False
    except Exception as e:
        logger.warning(f"ElevenLabs 失敗: {type(e).__name__}: {str(e)}")
        return False

def generate_audio_edge_tts(text, output_path):
    """使用 Edge TTS 生成音頻（方案2 - 主要備援）"""
    try:
        import edge_tts
        
        async def generate_tts():
            # 台灣中文女聲: zh-TW-HsiaoChenNeural (溫柔女聲)
            # 台灣中文男聲: zh-TW-YunJheNeural (男聲)
            communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural")
            temp_path = output_path + ".tmp.mp3"
            await communicate.save(temp_path)
            return temp_path
        
        temp_path = asyncio.run(generate_tts())
        logger.info("✓ 成功使用 Edge TTS 生成音頻")
        return temp_path
        
    except ImportError as e:
        logger.warning(f"Edge TTS 導入失敗: {e}")
        return False
    except Exception as e:
        logger.warning(f"Edge TTS 失敗: {type(e).__name__}: {str(e)}")
        return False

def generate_audio_coqui_tts(text, output_path):
    """使用 Coqui TTS 生成音頻（方案3 - 最終備援）"""
    try:
        from TTS.api import TTS
        
        logger.info("正在載入 Coqui TTS 模型（首次使用需要下載模型）...")
        
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        
        temp_path = output_path + ".tmp.wav"
        
        tts.tts_to_file(
            text=text,
            file_path=temp_path,
            language="zh-cn"
        )
        
        logger.info("✓ 成功使用 Coqui TTS 生成音頻")
        return temp_path
        
    except ImportError as e:
        logger.warning(f"Coqui TTS 導入失敗: {e}")
        return False
    except Exception as e:
        logger.warning(f"Coqui TTS 失敗: {type(e).__name__}: {str(e)}")
        return False

def post_process_audio(temp_path, output_path):
    """音頻後製處理"""
    try:
        # 根據檔案格式選擇載入方式
        if temp_path.endswith('.wav'):
            audio_segment = AudioSegment.from_wav(temp_path)
        else:
            audio_segment = AudioSegment.from_mp3(temp_path)
        
        # 音量正常化、設置取樣率和位元率
        audio_segment = audio_segment.normalize()
        audio_segment = audio_segment.set_frame_rate(44100).set_channels(2)
        audio_segment.export(output_path, format="mp3", bitrate="128k")
        
        logger.info(f"音頻後製完成: {output_path}")
        
        # 刪除臨時檔案
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return True
        
    except Exception as e:
        logger.error(f"音頻後製失敗: {str(e)}")
        return False

def generate_audio(text_path, output_path):
    """Generate audio from text using multiple TTS providers with fallback."""
    
    # 讀取文字檔案
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"讀取文字檔案成功，字數: {len(text)}")
    except Exception as e:
        logger.error(f"無法讀取文字檔案 {text_path}: {str(e)}")
        raise

    # 定義 TTS 提供商順序（按優先級）
    tts_providers = [
        ("ElevenLabs", generate_audio_elevenlabs),
        ("Edge TTS", generate_audio_edge_tts),
        ("Coqui TTS", generate_audio_coqui_tts)
    ]
    
    logger.info("開始嘗試使用 TTS 服務生成音頻...")
    
    temp_path = None
    for name, func in tts_providers:
        try:
            logger.info(f"嘗試使用 {name}...")
            temp_path = func(text, output_path)
            
            if temp_path:
                # 進行後製處理
                if post_process_audio(temp_path, output_path):
                    logger.success(f"✓ 使用 {name} 成功生成並處理音頻")
                    return
                else:
                    logger.warning(f"✗ {name} 後製處理失敗")
            else:
                logger.warning(f"✗ {name} 返回空結果")
                
        except Exception as e:
            logger.error(f"✗ {name} 異常: {type(e).__name__}: {str(e)}")
            continue
    
    # 所有方案都失敗
    logger.error("所有 TTS 服務皆不可用")
    raise RuntimeError("無法生成音頻：所有 TTS 服務皆失敗")
