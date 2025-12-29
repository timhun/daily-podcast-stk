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
            "Kevin Tu": "BrbEfHMQu0fyclQR7lfh",
        }
        
        client = ElevenLabs(api_key=api_key)
        voice_id = VOICE_IDS["Kevin Tu"]
        
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2"
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.0,
                "use_speaker_boost": True
            }
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
            # 使用穩定的語音選項
            voices = [
                "zh-TW-HsiaoChenNeural",  # 台灣中文女聲
                "zh-CN-XiaoxiaoNeural",  # 中國普通話女聲（更穩定）
            ]
            
            temp_path = output_path + ".tmp.mp3"
            
            for voice in voices:
                try:
                    logger.info(f"嘗試使用 Edge TTS 語音: {voice}")
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(temp_path)
                    logger.info(f"✓ 成功使用 Edge TTS ({voice}) 生成音頻")
                    return temp_path
                except Exception as e:
                    logger.warning(f"語音 {voice} 失敗: {str(e)}")
                    continue
            
            return False
        
        result = asyncio.run(generate_tts())
        return result
        
    except ImportError as e:
        logger.warning(f"Edge TTS 導入失敗: {e}")
        return False
    except Exception as e:
        logger.warning(f"Edge TTS 失敗: {type(e).__name__}: {str(e)}")
        return False

def generate_audio_gtts(text, output_path):
    """使用 Google TTS 生成音頻（方案3 - 簡單備援）"""
    try:
        from gtts import gTTS
        
        temp_path = output_path + ".tmp.mp3"
        
        # 使用 Google Text-to-Speech（簡單可靠）
        tts = gTTS(text=text, lang='zh-TW', slow=False)
        tts.save(temp_path)
        
        logger.info("✓ 成功使用 Google TTS 生成音頻")
        return temp_path
        
    except ImportError as e:
        logger.warning(f"Google TTS 導入失敗: {e}")
        return False
    except Exception as e:
        logger.warning(f"Google TTS 失敗: {type(e).__name__}: {str(e)}")
        return False

def generate_audio_pyttsx3(text, output_path):
    """使用 pyttsx3 生成音頻（方案4 - 離線備援）"""
    try:
        import pyttsx3
        
        temp_path = output_path + ".tmp.wav"
        
        engine = pyttsx3.init()
        
        # 設置語速和音量
        engine.setProperty('rate', 150)  # 語速
        engine.setProperty('volume', 1.0)  # 音量
        
        # 嘗試設置中文語音（如果可用）
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'chinese' in voice.name.lower() or 'mandarin' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        engine.save_to_file(text, temp_path)
        engine.runAndWait()
        
        logger.info("✓ 成功使用 pyttsx3 生成音頻")
        return temp_path
        
    except ImportError as e:
        logger.warning(f"pyttsx3 導入失敗: {e}")
        return False
    except Exception as e:
        logger.warning(f"pyttsx3 失敗: {type(e).__name__}: {str(e)}")
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
        ("Google TTS", generate_audio_gtts),
        ("pyttsx3", generate_audio_pyttsx3)
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
