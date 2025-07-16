from google.cloud import texttospeech
import datetime

def synthesize():
    with open("script.txt", "r", encoding="utf-8") as f:
        text = f.read()

    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="cmn-TW", name="cmn-TW-Standard-A"
    )

    audio_config = texttospeech.AudioConfig(
        speaking_rate=1.3,
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )

    date = datetime.date.today().isoformat()
    with open(f"episodes/{date}.mp3", "wb") as out:
        out.write(response.audio_content)

if __name__ == "__main__":
    synthesize()
