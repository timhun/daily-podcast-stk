import os
import subprocess

# 確保輸出資料夾存在
os.makedirs('podcast/latest', exist_ok=True)

input_file = 'podcast/latest/script.txt'
output_file = 'podcast/latest/audio.mp3'

# 確保 script.txt 存在
if not os.path.exists(input_file):
    raise FileNotFoundError("⚠️ 找不到 script.txt，無法合成語音")

# 讀取內容
with open(input_file, 'r', encoding='utf-8') as f:
    text = f.read()

# 呼叫 edge-tts 合成語音（台灣男聲，語速+30%）
subprocess.run([
    'edge-tts',
    '--voice', 'zh-TW-YunJheNeural',
    '--rate', '+30%',
    '--text', text,
    '--write-media', output_file
], check=True)

print("✅ 使用 edge-tts 已完成台灣口音語音合成 audio.mp3")
