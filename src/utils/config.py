from pathlib import Path
import os
from typing import Dict, Any
import yaml
from ..exceptions import ConfigError

class Config:
    """Centralized configuration management"""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent.parent
    CONF_DIR = BASE_DIR / "conf"
    DATA_DIR = BASE_DIR / "data"
    
    # File paths
    CATEGORY_MAPPING_FILE = os.getenv(
        'CATEGORY_MAPPING_FILE', 
        str(CONF_DIR / "category_mapping.yaml")
    )
    BANK_DATA_REGEX_FILE = os.getenv(
        'BANK_DATA_REGEX_FILE', 
        str(CONF_DIR / "bank_data_regex.yaml")
    )
    
    # Output directories
    OUTPUT_DIR = DATA_DIR / "csv"
    PDF_DIR = DATA_DIR / "statements"
    LOG_DIR = DATA_DIR / "logs"
    
    # Processing settings
    MAX_PDF_SIZE_MB = 50
    MAX_WORKERS = os.cpu_count() or 4
    
    @classmethod
    def load_yaml(cls, file_path: str) -> Dict[str, Any]:
        """Load and validate YAML configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load {file_path}: {e}")
    
    @classmethod
    def ensure_dirs(cls) -> None:
        """Ensure all required directories exist"""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.PDF_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True) 