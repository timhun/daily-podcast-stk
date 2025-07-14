import logging
from datetime import datetime
import os
import requests

def setup_logger():
    log_dir = "data/logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{log_dir}/podcast_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def log_error_and_notify(message, slack_webhook_url=None):
    logger = setup_logger()
    logger.error(message)
    if slack_webhook_url:
        try:
            requests.post(slack_webhook_url, json={'text': f"Podcast Error: {message}"})
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
    raise Exception(message)
