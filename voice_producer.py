#voice_
import asyncio
import edge_tts
from pydub import AudioSegment

async def async_generate_audio(text_path, output_path):
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()
    communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural", rate="+10%", pitch="+0Hz")
    await communicate.save(output_path)
    # 簡單後製: 音量正常化
    audio = AudioSegment.from_mp3(output_path)
    audio = audio.normalize()
    audio = audio.set_frame_rate(44100).set_channels(2)  # 設置 44.1kHz 取樣率與立體聲
    audio.export(output_path, format="mp3", bitrate="128k")  # 設置 128kbps 位元率

def generate_audio(text_path, output_path):
    asyncio.run(async_generate_audio(text_path, output_path))
