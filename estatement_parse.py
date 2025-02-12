import re
import csv
import yaml
import logging
import pdfplumber
from abc import ABC, abstractmethod
from collections import namedtuple
from pathlib import Path
from typing import List, Optional
from datetime import datetime

Transaction = namedtuple("Transaction", ["bank", "date", "amount", "description", "category"])

# YAML file paths
CATEGORY_MAPPING_FILE = "conf/category_mapping.yaml"
BANK_DATA_REGEX_FILE = "conf/bank_data_regex.yaml"

# ------------------------------------------------------------------------------
# 1. LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
# debug.log 依旧覆盖（w），info.log 采用追加（a）以保留历史记录
debug_handler = logging.FileHandler("debug.log", mode="w", encoding="utf-8")
debug_handler.setLevel(logging.DEBUG)

info_handler = logging.FileHandler("info.log", mode="w", encoding="utf-8")
info_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
debug_handler.setFormatter(formatter)
info_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers = [debug_handler, info_handler, console_handler]

# Suppress excessive logs from pdfplumber/pdminer, etc.
logging.getLogger("pdfplumber").setLevel(logging.INFO)
logging.getLogger("pdfminer").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 2. CODE FOR PARSING STATEMENTS
# ------------------------------------------------------------------------------

class Config:
    OUTPUT_DIR = Path("data/csv")
    PDF_DIR = Path("data/statements")
    
    @classmethod
    def ensure_dirs(cls):
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.PDF_DIR.mkdir(parents=True, exist_ok=True)


class PdfTextExtractor:
    """Mixin class for extracting text from PDF"""
    @staticmethod
    def _extract_text_from_pdf(pdf_path: Path) -> str:
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_path.name}: {e}")

        logger.debug(f"[PDF TEXT] of {pdf_path.name}:\n{text}\n---END---")
        return text


class BankStatementProcessor(ABC, PdfTextExtractor):
    """
    Abstract base class for Bank Statement Processors.
    Caches category mapping at class level.
    Also attempts to parse the 'statement_date' from text for year logic.
    """
    _category_mapping_cache = None

    def __init__(self, bank_name: str, category_mapping_file: str = CATEGORY_MAPPING_FILE):
        self.bank_name = bank_name
        # Load category mapping once
        if BankStatementProcessor._category_mapping_cache is None:
            BankStatementProcessor._category_mapping_cache = self._load_category_mapping(category_mapping_file)
        self.category_mapping = BankStatementProcessor._category_mapping_cache

        # statement_date 用于补充交易日期的年份 (datetime.date)
        self.statement_date: Optional[datetime.date] = None

    def _load_category_mapping(self, category_mapping_file: str):
        try:
            with open(category_mapping_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Category mapping file not found: {category_mapping_file}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file: {e}")
            return {}

    def categorize_transaction(self, description: str) -> str:
        """Categorize based on keywords in category_mapping.yaml."""
        description_upper = description.upper()
        for category, keywords in self.category_mapping.get("categories", {}).items():
            for keyword in keywords:
                if keyword.upper() in description_upper:
                    return category
        return "Other"

    def parse_date(self, date_str: str, fmt: str) -> Optional[datetime.date]:
        """
        Convert date_str (e.g. "14 Dec") using given format (e.g. '%d %b') into a date object.
        Then fix the year by comparing with self.statement_date:
          - If transaction month-day > statement month-day => year = statement_year - 1
          - Otherwise => year = statement_year
        If statement_date is not available or parse fails, fallback to None.
        """
        try:
            dt_no_year = datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            logger.warning(f"Cannot parse date string: '{date_str}' with format '{fmt}'")
            return None

        # If we don't have a statement_date, fallback to current year (or you can choose another logic)
        if not self.statement_date:
            fallback_year = datetime.now().year
            dt_no_year = dt_no_year.replace(year=fallback_year)
            logger.debug(f"No statement_date found, fallback to year={fallback_year} for date '{date_str}'")
            return dt_no_year.date()

        # Compare month-day
        st_mon, st_day = self.statement_date.month, self.statement_date.day
        tx_mon, tx_day = dt_no_year.month, dt_no_year.day

        # If transaction month-day > statement month-day => previous year
        if (tx_mon, tx_day) > (st_mon, st_day):
            year = self.statement_date.year - 1
        else:
            year = self.statement_date.year

        dt_final = dt_no_year.replace(year=year)
        return dt_final.date()

    @abstractmethod
    def extract_transactions(self, text: str) -> List[Transaction]:
        """Abstract method to extract transactions from text."""
        pass

    def extract_statement_date(self, text: str) -> Optional[datetime.date]:
        """
        Extract the statement date from text, e.g. "Payment Due Date January 09, 2025"
        Adjust the pattern to your actual PDF content. 
        """
        # 例： "Payment Due Date January 09, 2025"
        # 也可能是 "Payment Due Date : 09 Feb 2025", 所以需要多个pattern
        patterns = [
            r"[Dd]ue\s*Date\s*:?\s*(\d{1,2}\s[A-Za-z]{3}\s\d{4})",
            r"[Dd]ue\s*Date\s*([A-Za-z]{3,8}\s*\d{1,2}\,?\s*\d{4})"
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                date_str = m.group(1)
                logger.debug(f"Found statement date string: {date_str}")
                # 可能是 "January 09, 2025" or "Jan 09 2025" ...
                # 尝试多种格式
                possible_formats = ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%d %b %Y", "%B%d,%Y"]
                for fmt in possible_formats:
                    try:
                        dt_obj = datetime.strptime(date_str.strip(), fmt).date()
                        logger.debug(f"Parsed statement date with format '{fmt}': {dt_obj}")
                        return dt_obj  # Return a date object, not a string
                    except ValueError:
                        continue
                logger.warning(f"Failed to parse statement date with known formats: {date_str}")
        return None

    def process_pdf(self, pdf_path: Path) -> List[Transaction]:
        """Process a PDF file and extract transactions."""
        text = self._extract_text_from_pdf(pdf_path)

        # 先尝试从 PDF 文本中获取 statement_date
        self.statement_date = self.extract_statement_date(text)
        if self.statement_date:
            logger.info(f"Detected statement_date = {self.statement_date} for {pdf_path.name}")
        else:
            logger.info(f"No statement_date found for {pdf_path.name}, fallback to current year logic.")

        transactions = self.extract_transactions(text)
        logger.info(f"Extracted {len(transactions)} transactions from {pdf_path.name}")
        return transactions


class GenericBankProcessor(BankStatementProcessor):
    """
    A generic processor that uses the 'bank_data_regex.yaml' config
    to extract transactions by a single pattern and logic.
    """

    def __init__(self, bank_name: str, bank_config: dict, category_mapping_file: str = CATEGORY_MAPPING_FILE):
        super().__init__(bank_name, category_mapping_file)
        pattern_text = bank_config.get("pattern")
        self.regex = re.compile(pattern_text) if pattern_text else None

        self.date_group = bank_config.get("transaction_date_group")
        self.description_group = bank_config.get("description_group")
        self.amount_group = bank_config.get("amount_group")
        self.cr_group = bank_config.get("cr_group")  # optional
        self.invert_amount_if_cr = bank_config.get("invert_amount_if_cr", False)
        self.plus_means_negative = bank_config.get("plus_means_negative", False)
        self.date_format = bank_config.get("parse_date_format", "%d %b")

    def extract_transactions(self, text: str) -> List[Transaction]:
        if not self.regex:
            logger.error(f"No valid regex pattern configured for bank {self.bank_name}")
            return []

        matches = self.regex.findall(text)
        logger.debug(f"Regex found {len(matches)} matches for {self.bank_name}")

        transactions = []
        key_worlds = [
            'outstanding balance', 'Previous balance', 'Credit Payment',
            'PAYMENT VIA', "PREVIOUS STATEMENT", 'LATECHARGEFEE',
            'POSTING AMOUNT','CASHBACK','CASH BACK','CASH REBATE','LATE CHARGE'
        ]

        for match in matches:
            logger.debug(f"Matched groups: {match}")
            try:
                date_str = match[self.date_group].strip()
                description = match[self.description_group].strip()
                amount_str = match[self.amount_group].strip()

                # Skip blacklisted lines
                if any(kw.upper() in description.upper() for kw in key_worlds):
                    logger.info(f"Skipping transaction due to blacklisted keyword in: {description}")
                    continue

                # Clean up amount
                amount_str_clean = amount_str.replace("$", "").replace(",", "")

                # CR check
                cr_flag = ""
                if self.cr_group is not None and self.cr_group < len(match):
                    cr_flag = match[self.cr_group] or ""

                amount = float(amount_str_clean.replace("(", "").replace(")", ""))

                # Invert if CR
                if self.invert_amount_if_cr and cr_flag:
                    amount = -amount
                    logger.debug(f"Inverting amount due to CR flag: {amount}")

                # Invert if parentheses
                if "(" in amount_str and ")" in amount_str:
                    amount = -amount
                    logger.debug(f"Inverting amount due to parentheses: {amount}")

                # Invert if plus sign
                if self.plus_means_negative and amount_str_clean.startswith("+"):
                    amount = -amount
                    logger.debug(f"Inverting amount due to leading '+': {amount}")

                # Parse transaction date with statement_date logic
                trans_date_obj = self.parse_date(date_str, self.date_format)
                if not trans_date_obj:
                    continue

                category = self.categorize_transaction(description)
                transactions.append(Transaction(
                    bank=self.bank_name,
                    date=trans_date_obj,
                    amount=amount,
                    description=description,
                    category=category
                ))
            except (IndexError, ValueError) as e:
                logger.warning(f"Failed to parse match {match}: {e}")
                continue

        return transactions


def save_transactions(transactions: List[Transaction], output_file: Optional[Path] = None) -> None:
    """Save transactions to CSV (with mm/dd/yyyy date format) and handle validations."""
    if not transactions:
        logger.warning("No transactions to save.")
        return

    output_file = output_file or (Config.OUTPUT_DIR / f"transactions_{datetime.now():%Y%m%d}.csv")
    
    try:
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Bank", "Date", "Amount", "Description", "Category"])
            
            valid_count = 0
            for trans in transactions:
                if validate_transaction(trans):
                    # Format date as mm/dd/yyyy
                    date_str = trans.date.strftime("%m/%d/%Y")
                    writer.writerow([
                        trans.bank,
                        date_str,
                        trans.amount,
                        trans.description,
                        trans.category
                    ])
                    valid_count += 1
        logger.info(f"Saved {valid_count} valid transactions to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save transactions: {e}")
        raise


def validate_transaction(trans: Transaction) -> bool:
    """Simple validation for transaction fields."""
    try:
        assert trans.bank, "Bank is required"
        assert trans.date, "Date is required"
        assert isinstance(trans.amount, (int, float)), "Amount must be numeric"
        return True
    except AssertionError as err:
        logger.warning(f"Invalid transaction: {err} - {trans}")
        return False


def load_bank_regex_config() -> dict:
    """Load the bank_data_regex.yaml configuration file."""
    try:
        with open(BANK_DATA_REGEX_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("banks", {})
    except FileNotFoundError:
        logger.error(f"Bank regex config file not found: {BANK_DATA_REGEX_FILE}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse bank_data_regex.yaml: {e}")
        return {}


def detect_bank(text: str, bank_regex_data: dict) -> Optional[str]:
    """
    Attempt to detect which bank the PDF belongs to by searching for
    bank name keywords in the text. 
    """
    text_lower = text.lower()
    for bank_name in bank_regex_data.keys():
        if bank_name.lower() in text_lower:
            return bank_name
    return None


def get_bank_processor(pdf_file: Path, bank_regex_data: dict) -> Optional[GenericBankProcessor]:
    """
    Return a GenericBankProcessor if we can detect the bank from the PDF text,
    otherwise None.
    """
    text = PdfTextExtractor._extract_text_from_pdf(pdf_file)
    bank_name = detect_bank(text, bank_regex_data)
    if not bank_name:
        return None

    bank_config = bank_regex_data[bank_name]
    return GenericBankProcessor(bank_name, bank_config)


def main():
    Config.ensure_dirs()
    all_transactions = []

    bank_regex_data = load_bank_regex_config()
    if not bank_regex_data:
        logger.warning("No bank regex data available, cannot process.")
        return

    pdf_files = list(Config.PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {Config.PDF_DIR}")
        return

    for pdf_file in pdf_files:
        logger.info(f"Processing PDF: {pdf_file.name}")
        try:
            processor = get_bank_processor(pdf_file, bank_regex_data)
            if processor:
                transactions = processor.process_pdf(pdf_file)
                all_transactions.extend(transactions)
            else:
                logger.warning(f"Unrecognized bank for {pdf_file.name}")
        except Exception as e:
            logger.error(f"Failed to process {pdf_file.name}: {e}")
            continue

    if all_transactions:
        save_transactions(all_transactions)
    else:
        logger.warning("No transactions were processed.")


def test_single_pdf(pdf_path: str):
    """Debug function to parse a single PDF file, e.g. for local testing."""
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        logger.error(f"PDF file not found: {pdf_file}")
        return
    
    Config.ensure_dirs()
    bank_regex_data = load_bank_regex_config()
    if not bank_regex_data:
        logger.warning("No bank regex data available, cannot process.")
        return

    text = PdfTextExtractor._extract_text_from_pdf(pdf_file)
    logger.debug(f"Extracted text sample from {pdf_file.name}:\n{text[:3000]}...")

    bank_name = detect_bank(text, bank_regex_data)
    logger.debug(f"Detected bank: {bank_name}")
    
    if not bank_name:
        logger.error("Could not detect bank type from PDF text.")
        return
    
    processor = GenericBankProcessor(bank_name, bank_regex_data[bank_name])
    transactions = processor.process_pdf(pdf_file)

    logger.info(f"Found {len(transactions)} transactions in {pdf_file.name}")
    for trans in transactions:
        logger.info(f"Transaction: {trans}")

    return transactions


if __name__ == "__main__":
    try:
        main()
        # or for testing single PDF:
        # test_single_pdf("data/statements/YourSample.pdf")
    except Exception as e:
        logger.error(f"Program failed: {e}")
        raise
