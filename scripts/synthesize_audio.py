import os
import subprocess

os.makedirs('podcast/latest', exist_ok=True)

input_file = 'podcast/latest/script.txt'
output_file = 'podcast/latest/audio.mp3'

# edge-tts 語音合成
subprocess.run([
    'edge-tts',
    '--voice', 'zh-TW-YunJheNeural',
    '--rate', '+30%',
    '--text', open(input_file, 'r').read(),
    '--write-media', output_file
], check=True)

print("✅ 使用 edge-tts 已完成台灣口音語音合成")
