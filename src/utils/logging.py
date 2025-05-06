import logging
import logging.config
from pathlib import Path
from typing import Dict, Any
from ..utils.config import Config

class LogManager:
    """Enhanced logging configuration"""
    
    @staticmethod
    def setup_logging() -> None:
        """Setup logging configuration"""
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "simple": {
                    "format": "%(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": str(Config.LOG_DIR / "app.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5
                }
            },
            "loggers": {
                "": {  # Root logger
                    "handlers": ["console", "file"],
                    "level": "DEBUG"
                },
                "pdfplumber": {
                    "level": "INFO"
                },
                "pdfminer": {
                    "level": "INFO"
                }
            }
        }
        
        logging.config.dictConfig(config) 