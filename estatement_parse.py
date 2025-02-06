import re
import csv
from abc import ABC, abstractmethod
from collections import namedtuple
import yaml
import pdfplumber
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Define named tuple for transaction data structure
Transaction = namedtuple("Transaction", ["bank", "date", "amount", "description", "category"])

category_mapping_file = "conf/category_mapping.yaml"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Config:
    OUTPUT_DIR = Path("data/csv")
    PDF_DIR = Path("data/statements")
    
    @classmethod
    def ensure_dirs(cls):
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.PDF_DIR.mkdir(parents=True, exist_ok=True)


class PdfTextExtractor:
    """Mixin class for PDF text extraction"""

    @staticmethod
    def _extract_text_from_pdf(pdf_path):
        """Extract text content from PDF file."""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"PDF解析错误: {e}")
        #print(text[:5000])
        return text


class BankStatementProcessor(ABC, PdfTextExtractor):
    """银行账单处理器的抽象基类。"""

    def __init__(self, bank_name, category_mapping_file=category_mapping_file):
        """初始化银行账单处理器。"""
        self.bank_name = bank_name
        self.category_mapping = self._load_category_mapping(category_mapping_file)

    def _load_category_mapping(self, category_mapping_file):
        """从YAML文件加载类别映射配置。"""
        try:
            with open(category_mapping_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"找不到类别映射文件: {category_mapping_file}")
            return {}
        except yaml.YAMLError as e:
            print(f"解析YAML文件失败: {e}")
            return {}

    @abstractmethod
    def extract_transactions(self, text):
        """从账单文本中提取交易记录，这是一个抽象方法。"""
        pass

    def categorize_transaction(self, description):
        """根据交易描述确定交易类别。"""
        description = description.upper()
        for category, keywords in self.category_mapping.get("categories", {}).items():
            for keyword in keywords:
                if keyword.upper() in description:
                    return category
        return "Other"

    def process_pdf(self, pdf_path):
        """处理PDF文件并提取交易记录。"""
        text = self._extract_text_from_pdf(pdf_path)
        transactions = self.extract_transactions(text)
        print(f"从 {pdf_path} 提取到 {len(transactions)} 个交易记录")
        return transactions


class RegexTransactionExtractor:
    """ MixIn类,通过正则表达式提取transactions"""

    def __init__(self, transaction_regex):
        self.transaction_regex = transaction_regex

    def extract_transactions_by_regex(self, text):
        pattern = re.compile(self.transaction_regex, re.MULTILINE)
        matches = pattern.findall(text)
        #print(matches)
        return matches


class StandardCharteredProcessor(BankStatementProcessor, RegexTransactionExtractor):
    """处理Standard Chartered银行账单的交易记录。"""

    def __init__(self, category_mapping_file=category_mapping_file):
        #transaction_regex = r"(\d{2} \w{3})\s+(\d{2} \w{3})\s+([A-Za-z0-9\s\.\*\(\)\&,\'/-~\n]+?)\s+(-?\d+\.\d{2})([ ]?CR)?$"
        transaction_regex = r'(\d{2} \w{3})\s+(\d{2} \w{3})\s+([\w\s.*()&,\'"/-]+?)\s+(\d+\.\d{2})(CR)?$'
        RegexTransactionExtractor.__init__(self, transaction_regex)
        super().__init__("Standard Chartered", category_mapping_file)

    def extract_transactions(self, text):
        """从Standard Chartered账单中提取交易记录。"""
        transactions = []
        matches = self.extract_transactions_by_regex(text)

        for match in matches:
            trans_date, post_date, description, amount, cr = match

            # 排除带有括号的条目（如果有）
            if '(' in amount or ')' in amount:
                continue

            # 清理和转换金额
            try:
                amount = float(amount)
                if cr:
                    amount = -amount
            except ValueError:
                continue

            category = self.categorize_transaction(description)
            transactions.append(Transaction(self.bank_name, trans_date.strip(), amount, description.strip(), category))
        
        return transactions


class UOBProcessor(BankStatementProcessor, RegexTransactionExtractor):
    """处理UOB银行账单的交易记录。"""

    def __init__(self, category_mapping_file=category_mapping_file):
        #Amount强制要2位小数
        transaction_regex = r"(\d{2} \w{3})\s+(\d{2} \w{3})\s+([A-Za-z0-9\s.*()&,'-]+?)\s+(-?\$?\d+(?:\.\d{2}))"
        RegexTransactionExtractor.__init__(self, transaction_regex)
        super().__init__("UOB", category_mapping_file)

    def extract_transactions(self, text):
        """从UOB账单中提取交易记录。"""
        transactions = []
        matches = self.extract_transactions_by_regex(text)
        for match in matches:
            post_date, trans_date, description, amount = match
            amount = amount.replace("$", "").replace(",", "")
            amount = float(amount)
            category = self.categorize_transaction(description)
            transactions.append(Transaction(self.bank_name, trans_date, amount, description, category))
        return transactions


class CitibankProcessor(BankStatementProcessor, RegexTransactionExtractor):
    """处理Citibank银行账单的交易记录。"""

    def __init__(self, category_mapping_file=category_mapping_file):
        # Regex pattern to match Citibank transactions:
        # (\d{2}[A-Z]{3}) - Matches date in format like "14NOV" 
        # \s+ - One or more whitespace
        # ([A-Za-z0-9*/\-&\s]+?) - Description containing letters, numbers, symbols
        # \s+SGD?\s+ - "SGD" currency code with optional whitespace
        # (-?\d+\.\d{2}) - Amount with 2 decimal places, optional negative sign
        transaction_regex = r'(\d{2}[A-Z]{3})\s+(.+?)\s+SGD?\s+(-?\d+\.\d{2})'
        RegexTransactionExtractor.__init__(self, transaction_regex)
        super().__init__("Citibank", category_mapping_file)

    def extract_transactions(self, text):
        """从Citibank账单中提取交易记录。"""
        transactions = []
        matches = self.extract_transactions_by_regex(text)
        for match in matches:
            date, description, amount = match
            amount = amount.replace("(", "").replace(")", "").replace("$", "").replace(",", "").strip()
            try:
                amount = float(amount)
                if '(' in match[2] and ')' in match[2]:
                    amount = -amount
            except ValueError:
                continue
            category = self.categorize_transaction(description)
            transactions.append(Transaction(self.bank_name, date.strip(), amount, description.strip(), category))
        return transactions


class TrustProcessor(BankStatementProcessor, RegexTransactionExtractor):
    """处理Trust银行账单的交易记录。"""

    def __init__(self, category_mapping_file=category_mapping_file):
        #(?!Previous balance): 负向断言，即排除特定字符
        transaction_regex = r"([1-3][0-9]\s\w{3})\s+((?!Previous balance)(?!outstanding balance).*)\s+(\+?\d+\.\d{2})"
        RegexTransactionExtractor.__init__(self, transaction_regex)
        super().__init__("Trust", category_mapping_file)

    def extract_transactions(self, text):
        """从Trust银行账单中提取交易记录。"""
        transactions = []
        matches = self.extract_transactions_by_regex(text)
        for match in matches:
            date, description, amount = match
            amount = amount.replace("$", "").replace(",", "")
            if "+" in amount:
                amount = -float(amount)
            amount = float(amount)
            category = self.categorize_transaction(description)
            transactions.append(Transaction(self.bank_name, date, amount, description, category))
        return transactions


def save_transactions(transactions: List[Transaction], 
                     output_file: Optional[Path] = None) -> None:
    """Save transactions to CSV with error handling and validation."""
    if not transactions:
        logging.warning("No transactions to save")
        return

    output_file = output_file or Config.OUTPUT_DIR / f"transactions_{datetime.now():%Y%m%d}.csv"
    
    try:
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            #writer.writerow(["Bank", "Date", "Amount", "Description", "Category"])
            
            for trans in transactions:
                if validate_transaction(trans):
                    writer.writerow([
                        trans.bank, 
                        trans.date, 
                        trans.amount, 
                        trans.description, 
                        trans.category
                    ])
        
        logging.info(f"Saved {len(transactions)} transactions to {output_file}")
    except Exception as e:
        logging.error(f"Failed to save transactions: {e}")
        raise

def validate_transaction(trans: Transaction) -> bool:
    """Validate transaction data."""
    try:
        assert trans.bank, "Bank is required"
        assert trans.date, "Date is required"
        assert isinstance(trans.amount, (int, float)), "Amount must be numeric"
        return True
    except AssertionError as e:
        logging.warning(f"Invalid transaction: {e} - {trans}")
        return False

def get_bank_processor(pdf_file):
    """Determine the bank processor based on the PDF file content."""
    text = PdfTextExtractor._extract_text_from_pdf(pdf_file)
    logging.info(f"Extracted text from {pdf_file.name}")
    
    bank_processors = {
        "Standard Chartered": StandardCharteredProcessor(),
        "UOB": UOBProcessor(),
        "Citibank": CitibankProcessor(),
        "Trust": TrustProcessor()
    }
    
    for bank_name in bank_processors:
        if bank_name.lower() in text.lower():
            return bank_processors[bank_name]
    
    return None

def main():
    """Main program with improved error handling and logging."""
    Config.ensure_dirs()
    all_transactions = []
    
    pdf_files = list(Config.PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        logging.warning(f"No PDF files found in {Config.PDF_DIR}")
        return
    
    for pdf_file in pdf_files:
        try:
            logging.info(f"Processing {pdf_file.name}")
            processor = get_bank_processor(pdf_file)
            if processor:
                transactions = processor.process_pdf(pdf_file)
                all_transactions.extend(transactions)
            else:
                logging.warning(f"Unrecognized bank type for {pdf_file.name}")
        except Exception as e:
            logging.error(f"Failed to process {pdf_file.name}: {e}")
            continue
    
    if all_transactions:
        save_transactions(all_transactions)
    else:
        logging.warning("No transactions were processed")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Program failed: {e}")
        raise