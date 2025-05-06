from pathlib import Path
from typing import Union
from ..exceptions import ValidationError
from ..utils.config import Config
from ..models.transaction import Transaction

class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_pdf_path(pdf_path: Union[str, Path]) -> Path:
        """Validate PDF file path and existence"""
        path = Path(pdf_path)
        
        if not path.exists():
            raise ValidationError(f"PDF file not found: {path}")
            
        if path.suffix.lower() != '.pdf':
            raise ValidationError(f"File must be a PDF: {path}")
            
        if path.stat().st_size > Config.MAX_PDF_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"PDF file too large: {path}")
            
        return path
    
    @staticmethod
    def validate_transaction(trans: Transaction) -> bool:
        """Validate transaction data"""
        if not trans.bank:
            raise ValidationError("Bank name is required")
            
        if not trans.date:
            raise ValidationError("Transaction date is required")
            
        if not isinstance(trans.amount, (int, float)):
            raise ValidationError("Amount must be numeric")
            
        return True 