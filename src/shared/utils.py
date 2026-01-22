import logging
import sys
import time
import random
import requests
from src.config.settings import config

def get_logger(service_name: str) -> logging.Logger:
    """Genera un logger estandarizado para todo el sistema"""
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(config.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(config.LOG_LEVEL)
    return logger

def robust_http_request(method: str, url: str, json_data: dict = None, max_retries: int = 3):
    """Realiza peticiones HTTP con Exponential Backoff (Circuit Breaker Light)"""
    logger = get_logger("SharedNetwork")
    for i in range(max_retries):
        try:
            if method == 'POST':
                resp = requests.post(url, json=json_data, timeout=5)
            else:
                resp = requests.get(url, timeout=5)
            return resp
        except requests.RequestException as e:
            wait = (0.5 * (2 ** i)) + random.uniform(0, 0.1)
            if i == max_retries - 1:
                logger.error(f"❌ Network fail after {max_retries} tries: {url} | {e}")
                raise e
            time.sleep(wait)
