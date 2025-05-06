import logging
from pathlib import Path
from typing import List, Optional
import pandas as pd
from ..models.transaction import Transaction
from ..utils.config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class TransactionExporter:
    """Enhanced transaction export functionality"""
    
    @staticmethod
    def to_csv(transactions: List[Transaction], path: Optional[Path] = None) -> Path:
        """Export transactions to CSV"""
        if not transactions:
            logger.warning("No transactions to export")
            return None
            
        path = path or (Config.OUTPUT_DIR / f"transactions_{datetime.now():%Y%m%d}.csv")
        df = pd.DataFrame([vars(t) for t in transactions])
        df.to_csv(path, index=False)
        logger.info(f"Exported {len(transactions)} transactions to CSV: {path}")
        return path
    
    @staticmethod
    def to_excel(transactions: List[Transaction], path: Optional[Path] = None) -> Path:
        """Export transactions to Excel"""
        if not transactions:
            logger.warning("No transactions to export")
            return None
            
        path = path or (Config.OUTPUT_DIR / f"transactions_{datetime.now():%Y%m%d}.xlsx")
        df = pd.DataFrame([vars(t) for t in transactions])
        df.to_excel(path, index=False)
        logger.info(f"Exported {len(transactions)} transactions to Excel: {path}")
        return path
    
    @staticmethod
    def to_json(transactions: List[Transaction], path: Optional[Path] = None) -> Path:
        """Export transactions to JSON"""
        if not transactions:
            logger.warning("No transactions to export")
            return None
            
        path = path or (Config.OUTPUT_DIR / f"transactions_{datetime.now():%Y%m%d}.json")
        df = pd.DataFrame([vars(t) for t in transactions])
        df.to_json(path, orient='records')
        logger.info(f"Exported {len(transactions)} transactions to JSON: {path}")
        return path 