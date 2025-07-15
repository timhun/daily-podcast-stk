from gtts import gTTS
import os
from datetime import datetime

def text_to_audio(script, output_file):
    tts = gTTS(text=script, lang='zh-tw', slow=False)
    tts.save(output_file)
    return output_file

if __name__ == '__main__':
    with open('script.txt', 'r', encoding='utf-8') as f:
        script = f.read()
    date = datetime.now().strftime('%Y%m%d')
    output_file = f'audio/episode_{date}.mp3'
    text_to_audio(script, output_file)
