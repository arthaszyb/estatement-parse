import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache
import pdfplumber
from ..models.transaction import Transaction
from ..exceptions import PDFParseError
from ..utils.config import Config
from datetime import date

logger = logging.getLogger(__name__)

class PdfTextExtractor:
    """Mixin for PDF text extraction"""
    
    @staticmethod
    def _extract_text_from_pdf(pdf_path: Path) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise PDFParseError(f"Failed to parse PDF {pdf_path.name}: {e}")
            
        logger.debug(f"[PDF TEXT] of {pdf_path.name}:\n{text}\n---END---")
        return text

class BankStatementProcessor(ABC, PdfTextExtractor):
    """Base class for bank statement processors"""
    
    def __init__(self, bank_name: str, config: Dict[str, Any]):
        self.bank_name = bank_name
        self.config = config
        self._category_cache = {}
        self.statement_date: Optional[date] = None
    
    @lru_cache(maxsize=128)
    def categorize_transaction(self, description: str) -> str:
        """Cached transaction categorization"""
        description_upper = description.upper()
        for category, keywords in self.config.get("categories", {}).items():
            for keyword in keywords:
                if keyword.upper() in description_upper:
                    return category
        return "Other"
    
    def process_pdf(self, pdf_path: Path) -> List[Transaction]:
        """Process PDF with performance monitoring"""
        start_time = time.time()
        try:
            result = self._process_pdf_impl(pdf_path)
            processing_time = time.time() - start_time
            logger.info(f"Processed {pdf_path.name} in {processing_time:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            raise
    
    @abstractmethod
    def _process_pdf_impl(self, pdf_path: Path) -> List[Transaction]:
        """Implementation of PDF processing logic"""
        pass 