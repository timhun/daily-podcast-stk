from google.cloud import texttospeech
from datetime import datetime
import os
from logger import setup_logger, log_error_and_notify

logger = setup_logger()

def text_to_audio(script, output_file):
    try:
        client = texttospeech.TextToSpeechClient.from_service_account_json('credentials.json')
        synthesis_input = texttospeech.SynthesisInput(text=script)
        voice = texttospeech.VoiceSelectionParams(
            language_code="cmn-TW",
            name="cmn-TW-Standard-A",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.3,
            pitch=0.0,
            sample_rate_hertz=44100
        )
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        with open(output_file, 'wb') as f:
            f.write(response.audio_content)
        logger.info(f"Audio generated: {output_file}")
        return output_file
    except Exception as e:
        log_error_and_notify(f"Error generating audio: {str(e)}", os.getenv('SLACK_WEBHOOK_URL'))

if __name__ == "__main__":
    with open('data/script.txt', 'r', encoding='utf-8') as f:
        script = f.read()
    date = datetime.now().strftime('%Y%m%d')
    output_file = f'audio/episode_{date}.mp3'
    text_to_audio(script, output_file)
