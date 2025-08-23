# scripts/utils.py
import logging
import json
import os
from datetime import datetime
import pytz
from openai import OpenAI

def setup_json_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(f"logs/{name}.json", mode='a')
    formatter = logging.Formatter('{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": %(message)s}')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def get_grok_client():
    return OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ['GROK_API_KEY'])

def get_taiwan_time():
    return datetime.now(pytz.timezone('Asia/Taipei'))

def slack_alert(message, channel=os.environ['SLACK_CHANNEL']):
    from slack_sdk import WebClient
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
    client.chat_postMessage(channel=channel, text=message)
