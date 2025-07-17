import subprocess

script_file = "podcast/latest/script.txt"
audio_file = "podcast/latest/audio.mp3"
with open(script_file) as f:
    content = f.read()

subprocess.run([
    "edge-tts", "--voice", "zh-TW-YunJheNeural",
    "--rate=+30%",
    "--text", content,
    "--output", audio_file
])