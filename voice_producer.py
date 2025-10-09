import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from pydub import AudioSegment
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

def generate_audio(text_path, output_path):
    """Generate audio from text using ElevenLabs API and apply post-processing."""
    # 檢查 ElevenLabs API 密鑰
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ELEVENLABS_API_KEY 未設置")
        raise ValueError("ELEVENLABS_API_KEY not set")

    # 初始化 ElevenLabs 客戶端
    client = ElevenLabs(api_key=api_key)

    # 讀取文字檔案
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        logger.error(f"無法讀取文字檔案 {text_path}: {str(e)}")
        raise

    # 使用 ElevenLabs 生成音頻
    try:
        # 使用預設的多語言語音或列出可用語音
        # 常見的多語言語音 ID：
        # "pNInz6obpgDQGcFmaJgB" - Adam (multilingual)
        # "21m00Tcm4TlvDq8ikWAM" - Rachel (English, but clear)
        
        # 嘗試獲取可用語音列表並選擇支援中文的
        try:
            voices = client.voices.get_all()
            # 尋找支援多語言的語音
            multilingual_voice = None
            for voice in voices.voices:
                # 優先選擇名為 Aria 的語音（如果存在）
                if voice.name.lower() == "aria":
                    multilingual_voice = voice.voice_id
                    logger.info(f"找到 Aria 語音: {voice.voice_id}")
                    break
            
            # 如果沒找到 Aria，使用第一個多語言語音
            if not multilingual_voice:
                for voice in voices.voices:
                    # 檢查語音是否支援多語言
                    if hasattr(voice, 'labels') and voice.labels:
                        if 'multilingual' in str(voice.labels).lower():
                            multilingual_voice = voice.voice_id
                            logger.info(f"使用多語言語音: {voice.name} ({voice.voice_id})")
                            break
            
            # 如果還是沒找到，使用第一個可用語音
            if not multilingual_voice and voices.voices:
                multilingual_voice = voices.voices[0].voice_id
                logger.warning(f"使用預設語音: {voices.voices[0].name} ({multilingual_voice})")
            
            voice_id = multilingual_voice or "pNInz6obpgDQGcFmaJgB"  # 備用 voice ID
            
        except Exception as e:
            logger.warning(f"無法獲取語音列表: {str(e)}, 使用預設語音")
            voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam - 多語言語音
        
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2"
        )
        logger.info(f"成功使用 ElevenLabs API 生成音頻: {output_path}")

        # 保存音頻到臨時檔案
        temp_path = output_path + ".tmp.mp3"
        save(audio, temp_path)
    except Exception as e:
        logger.error(f"ElevenLabs API 失敗: {str(e)}")
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