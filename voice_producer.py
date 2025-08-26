import asyncio
import edge_tts
from pydub import AudioSegment

async def async_generate_audio(text_path, output_path):
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()
    communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural", rate="+5%")
    await communicate.save(output_path)
    # 簡單後製: 音量正常化
    audio = AudioSegment.from_mp3(output_path)
    audio = audio.normalize()
    audio.export(output_path, format="mp3")

def generate_audio(text_path, output_path):
    asyncio.run(async_generate_audio(text_path, output_path))
