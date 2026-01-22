import logging
import sys
from src.config.settings import settings

def setup_logger(name: str) -> logging.Logger:
    """Configura un logger profesional con formato estandarizado"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(settings.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
