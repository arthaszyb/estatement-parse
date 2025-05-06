import re
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from .base import BankStatementProcessor
from ..models.transaction import Transaction
from ..exceptions import TransactionParseError
from ..utils.validators import InputValidator
from ..utils.config import Config

logger = logging.getLogger(__name__)

def is_leap_year(year: int) -> bool:
    """Check if a year is a leap year"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

class GenericBankProcessor(BankStatementProcessor):
    """Generic processor for bank statements"""
    
    def __init__(self, bank_name: str, bank_config: Dict[str, Any]):
        # 加载分类规则
        try:
            with open(Config.CATEGORY_MAPPING_FILE, "r", encoding="utf-8") as f:
                category_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load category mapping: {e}")
            category_config = {}
            
        # 将分类规则和银行配置合并
        config = {**bank_config, "categories": category_config.get("categories", {})}
        super().__init__(bank_name, config)
        
        pattern_text = bank_config.get("pattern")
        self.regex = re.compile(pattern_text) if pattern_text else None
        self.date_group = bank_config.get("transaction_date_group")
        self.description_group = bank_config.get("description_group")
        self.amount_group = bank_config.get("amount_group")
        self.cr_group = bank_config.get("cr_group")
        self.invert_amount_if_cr = bank_config.get("invert_amount_if_cr", False)
        self.plus_means_negative = bank_config.get("plus_means_negative", False)
        self.date_format = bank_config.get("parse_date_format", "%d %b")
    
    def _extract_statement_date(self, text: str) -> Optional[date]:
        """Extract statement date from PDF text"""
        patterns = [
            r"Statement Date:\s*(\d{1,2}\s[A-Za-z]{3}\s\d{4})",
            r"Statement Date:\s*([A-Za-z]{3,8}\s*\d{1,2},?\s*\d{4})",
            r"Due Date:\s*(\d{1,2}\s[A-Za-z]{3}\s\d{4})",
            r"Due Date:\s*([A-Za-z]{3,8}\s*\d{1,2},?\s*\d{4})",
            r"Date:\s*(\d{1,2}\s[A-Za-z]{3}\s\d{4})",
            r"Date:\s*([A-Za-z]{3,8}\s*\d{1,2},?\s*\d{4})",
            r"(\d{1,2}\s[A-Za-z]{3}\s\d{4})",  # Fallback pattern
            r"([A-Za-z]{3,8}\d{1,2},?\d{4})",  # Format like "April15,2025"
            r"(\d{1,2}\s[A-Za-z]{3}\s\d{2})",  # Format like "15 Apr 25"
            r"([A-Za-z]{3,8}\s*\d{1,2},?\s*\d{2})",  # Format like "April 15, 25"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                logger.debug(f"Found statement date string: {date_str}")
                
                # Try different date formats
                possible_formats = [
                    "%d %b %Y",  # 31 Jan 2024
                    "%B %d, %Y",  # January 31, 2024
                    "%B %d %Y",   # January 31 2024
                    "%b %d, %Y",  # Jan 31, 2024
                    "%b %d %Y",   # Jan 31 2024
                    "%d%b%Y",     # 31Jan2024
                    "%d %B %Y",   # 31 January 2024
                    "%B%d,%Y",    # April15,2025
                    "%B%d%Y",     # April152025
                    "%d %b %y",   # 15 Apr 25
                    "%B %d, %y",  # April 15, 25
                    "%B %d %y",   # April 15 25
                ]
                
                for fmt in possible_formats:
                    try:
                        dt = datetime.strptime(date_str.strip(), fmt).date()
                        logger.debug(f"Successfully parsed statement date: {dt} with format {fmt}")
                        return dt
                    except ValueError:
                        continue
                        
                logger.warning(f"Failed to parse statement date with known formats: {date_str}")
                
        logger.warning("No statement date found in text")
        return None
    
    def _process_pdf_impl(self, pdf_path: Path) -> List[Transaction]:
        """Implementation of PDF processing logic"""
        if not self.regex:
            logger.error(f"No valid regex pattern configured for bank {self.bank_name}")
            return []
            
        text = self._extract_text_from_pdf(pdf_path)
        
        # Extract statement date
        self.statement_date = self._extract_statement_date(text)
        if not self.statement_date:
            logger.warning(f"Could not extract statement date from {pdf_path.name}, will use current year as fallback")
            self.statement_date = datetime.now().date()
            
        matches = self.regex.findall(text)
        logger.debug(f"Regex found {len(matches)} matches for {self.bank_name}")
        
        transactions = []
        key_words = [
            "outstanding balance",
            "Previous balance",
            "Credit Payment",
            "PAYMENT VIA",
            "PREVIOUS STATEMENT",
            "LATECHARGEFEE",
            "POSTING AMOUNT",
            "CASHBACK",
            "CASH BACK",
            "CASH REBATE",
            "LATE CHARGE",
        ]
        
        for match in matches:
            try:
                date_str = match[self.date_group].strip()
                description = match[self.description_group].strip()
                amount_str = match[self.amount_group].strip()
                
                # Skip blacklisted keywords
                if any(kw.upper() in description.upper() for kw in key_words):
                    logger.info(f"Skipping transaction due to blacklisted keyword in: {description}")
                    continue
                
                # Process amount
                amount_str_clean = amount_str.replace("$", "").replace(",", "")
                cr_flag = ""
                if self.cr_group is not None and self.cr_group < len(match):
                    cr_flag = match[self.cr_group] or ""
                
                amount = float(amount_str_clean.replace("(", "").replace(")", ""))
                
                if self.invert_amount_if_cr and cr_flag:
                    amount = -amount
                if "(" in amount_str and ")" in amount_str:
                    amount = -amount
                if self.plus_means_negative and amount_str_clean.startswith("+"):
                    amount = -amount
                
                # Parse date
                trans_date = self._parse_date(date_str)
                if not trans_date:
                    continue
                
                # Create transaction
                transaction = Transaction(
                    bank=self.bank_name,
                    date=trans_date,
                    amount=amount,
                    description=description,
                    category=self.categorize_transaction(description)
                )
                
                # Validate transaction
                InputValidator.validate_transaction(transaction)
                transactions.append(transaction)
                
            except (IndexError, ValueError) as e:
                logger.warning(f"Failed to parse match {match}: {e}")
                continue
                
        return transactions
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string with format handling"""
        try:
            # First try parsing with the configured format
            dt = datetime.strptime(date_str.strip(), self.date_format)
            
            # Get current date
            current_date = datetime.now().date()
            current_year = current_date.year
            
            # Create a date with current year for comparison
            trans_date_with_current_year = dt.replace(year=current_year).date()
            
            # If transaction date is in the future compared to current date,
            # it's likely from the previous year
            if trans_date_with_current_year > current_date:
                year = current_year - 1
            else:
                year = current_year
                
            dt = dt.replace(year=year)
            logger.debug(f"Setting year to {year} for date '{date_str}' (current year: {current_year})")
            return dt.date()
            
        except ValueError as e:
            logger.warning(f"Failed to parse date: {date_str} with format {self.date_format}")
            return None 