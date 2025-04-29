import re
import csv
import yaml
import logging
import logging.config
import pdfplumber
import concurrent.futures
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from datetime import datetime, date
from dataclasses import dataclass


# ------------------------------------------------------------------------------
# 1. DATA MODEL (使用 dataclass 替代 namedtuple)
# ------------------------------------------------------------------------------
@dataclass
class Transaction:
    bank: str
    date: date
    amount: float
    description: str
    category: str


# YAML file paths 保持不变
CATEGORY_MAPPING_FILE = "conf/category_mapping.yaml"
BANK_DATA_REGEX_FILE = "conf/bank_data_regex.yaml"

# ------------------------------------------------------------------------------
# 2. LOGGING CONFIGURATION (使用 dictConfig 进行配置)
# ------------------------------------------------------------------------------
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s"},
    },
    "handlers": {
        "debug_file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "default",
            "filename": "debug.log",
            "mode": "w",
            "encoding": "utf-8",
        },
        "info_file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "formatter": "default",
            "filename": "info.log",
            "mode": "a",
            "encoding": "utf-8",
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {"level": "DEBUG", "handlers": ["debug_file", "info_file", "console"]},
}

logging.config.dictConfig(LOGGING_CONFIG)

# 限制第三方库日志输出
logging.getLogger("pdfplumber").setLevel(logging.INFO)
logging.getLogger("pdfminer").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 3. 代码主体：配置、PDF文本提取、解析逻辑
# ------------------------------------------------------------------------------


class Config:
    OUTPUT_DIR = Path("data/csv")
    PDF_DIR = Path("data/statements")

    @classmethod
    def ensure_dirs(cls):
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.PDF_DIR.mkdir(parents=True, exist_ok=True)


class PdfTextExtractor:
    """Mixin，用于从 PDF 中提取文本"""

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
    银行账单处理器基类。
    类级缓存分类映射，同时通过 PDF 文本中提取 statement_date 来辅助日期逻辑。
    """

    _category_mapping_cache = None

    def __init__(
        self, bank_name: str, category_mapping_file: str = CATEGORY_MAPPING_FILE
    ):
        self.bank_name = bank_name
        if BankStatementProcessor._category_mapping_cache is None:
            BankStatementProcessor._category_mapping_cache = (
                self._load_category_mapping(category_mapping_file)
            )
        self.category_mapping = BankStatementProcessor._category_mapping_cache
        self.statement_date: Optional[date] = None

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
        description_upper = description.upper()
        for category, keywords in self.category_mapping.get("categories", {}).items():
            for keyword in keywords:
                if keyword.upper() in description_upper:
                    return category
        return "Other"


    def parse_date(self, date_str: str, fmt: str) -> Optional[date]:
        """
        将不包含年份的日期字符串转换为完整的日期对象。
        针对"29 Feb"这种情况，如果默认解析年份（如1900）导致错误，则采用2000作为默认解析年份。
        然后根据 statement_date 或当前年份来调整年份，
        如果解析的是2月29日但目标年份不是闰年，则自动寻找最近的有效闰年。
        """
        stripped = date_str.strip()
        try:
            dt_no_year = datetime.strptime(stripped, fmt)
        except ValueError:
            # 针对 "%d %b" 格式，处理类似 "29 Feb" 的情况
            parts = stripped.split()
            if len(parts) == 2:
                try:
                    day = int(parts[0])
                    # 使用 %b 格式解析月份缩写
                    month = datetime.strptime(parts[1], "%b").month
                except Exception as e:
                    logger.warning(
                        f"Cannot parse date string: '{date_str}' with format '{fmt}'"
                    )
                    return None
                if day == 29 and month == 2:
                    # 2000是闰年，使用它作为默认年份进行解析
                    dt_no_year = datetime(2000, 2, 29)
                else:
                    logger.warning(
                        f"Cannot parse date string: '{date_str}' with format '{fmt}'"
                    )
                    return None
            else:
                logger.warning(
                    f"Cannot parse date string: '{date_str}' with format '{fmt}'"
                )
                return None

        # 调整年份
        if not self.statement_date:
            fallback_year = datetime.now().year
            # 如果解析的是2月29日，但 fallback_year 不是闰年，则寻找下一个闰年
            if (
                dt_no_year.month == 2
                and dt_no_year.day == 29
                and not is_leap_year(fallback_year)
            ):
                while not is_leap_year(fallback_year):
                    fallback_year += 1
            dt_final = dt_no_year.replace(year=fallback_year)
            logger.debug(
                f"No statement_date found, fallback to year={fallback_year} for date '{date_str}'"
            )
            return dt_final.date()
        else:
            st_mon, st_day = self.statement_date.month, self.statement_date.day
            tx_mon, tx_day = dt_no_year.month, dt_no_year.day
            year = (
                self.statement_date.year - 1
                if (tx_mon, tx_day) > (st_mon, st_day)
                else self.statement_date.year
            )
            # 如果交易日期为2月29日，但计算得到的年份不是闰年，则向前寻找最近的闰年
            if dt_no_year.month == 2 and dt_no_year.day == 29 and not is_leap_year(year):
                while not is_leap_year(year):
                    year -= 1
            return dt_no_year.replace(year=year).date()

    @abstractmethod
    def extract_transactions(self, text: str) -> List[Transaction]:
        """抽象方法，从文本中提取交易记录。"""
        pass

    def extract_statement_date(self, text: str) -> Optional[date]:
        patterns = [
            r"[Dd]ue\s*Date\s*:?\s*(\d{1,2}\s[A-Za-z]{3}\s\d{4})",
            r"[Dd]ue\s*Date\s*([A-Za-z]{3,8}\s*\d{1,2}\,?\s*\d{4})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                date_str = m.group(1)
                logger.debug(f"Found statement date string: {date_str}")
                possible_formats = [
                    "%B %d, %Y",
                    "%B %d %Y",
                    "%b %d, %Y",
                    "%b %d %Y",
                    "%d %b %Y",
                    "%B%d,%Y",
                ]
                for fmt in possible_formats:
                    try:
                        dt_obj = datetime.strptime(date_str.strip(), fmt).date()
                        logger.debug(
                            f"Parsed statement date with format '{fmt}': {dt_obj}"
                        )
                        return dt_obj
                    except ValueError:
                        continue
                logger.warning(
                    f"Failed to parse statement date with known formats: {date_str}"
                )
        return None

    def process_pdf(self, pdf_path: Path) -> List[Transaction]:
        text = self._extract_text_from_pdf(pdf_path)
        self.statement_date = self.extract_statement_date(text)
        if self.statement_date:
            logger.info(
                f"Detected statement_date = {self.statement_date} for {pdf_path.name}"
            )
        else:
            logger.info(
                f"No statement_date found for {pdf_path.name}, fallback to current year logic."
            )
        transactions = self.extract_transactions(text)
        logger.info(f"Extracted {len(transactions)} transactions from {pdf_path.name}")
        return transactions


def clean_amount(amount_str: str) -> str:
    """辅助函数，清理金额字符串中的 '$' 和逗号。"""
    return amount_str.replace("$", "").replace(",", "")


def parse_float_amount(amount_str: str) -> float:
    """辅助函数，将金额字符串转换为浮点数，并处理括号。"""
    return float(amount_str.replace("(", "").replace(")", ""))


class GenericBankProcessor(BankStatementProcessor):
    """
    通用处理器，根据 bank_data_regex.yaml 中的配置提取交易记录。
    """

    def __init__(
        self,
        bank_name: str,
        bank_config: dict,
        category_mapping_file: str = CATEGORY_MAPPING_FILE,
    ):
        super().__init__(bank_name, category_mapping_file)
        pattern_text = bank_config.get("pattern")
        self.regex = re.compile(pattern_text) if pattern_text else None
        self.date_group = bank_config.get("transaction_date_group")
        self.description_group = bank_config.get("description_group")
        self.amount_group = bank_config.get("amount_group")
        self.cr_group = bank_config.get("cr_group")
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
            logger.debug(f"Matched groups: {match}")
            try:
                date_str = match[self.date_group].strip()
                description = match[self.description_group].strip()
                amount_str = match[self.amount_group].strip()

                # 跳过包含黑名单关键字的交易记录
                if any(kw.upper() in description.upper() for kw in key_words):
                    logger.info(
                        f"Skipping transaction due to blacklisted keyword in: {description}"
                    )
                    continue

                amount_str_clean = clean_amount(amount_str)
                cr_flag = ""
                if self.cr_group is not None and self.cr_group < len(match):
                    cr_flag = match[self.cr_group] or ""

                amount = parse_float_amount(amount_str_clean)

                if self.invert_amount_if_cr and cr_flag:
                    amount = -amount
                    logger.debug(f"Inverting amount due to CR flag: {amount}")
                if "(" in amount_str and ")" in amount_str:
                    amount = -amount
                    logger.debug(f"Inverting amount due to parentheses: {amount}")
                if self.plus_means_negative and amount_str_clean.startswith("+"):
                    amount = -amount
                    logger.debug(f"Inverting amount due to leading '+': {amount}")

                trans_date_obj = self.parse_date(date_str, self.date_format)
                if not trans_date_obj:
                    continue

                category = self.categorize_transaction(description)
                transactions.append(
                    Transaction(
                        bank=self.bank_name,
                        date=trans_date_obj,
                        amount=amount,
                        description=description,
                        category=category,
                    )
                )
            except (IndexError, ValueError) as e:
                logger.warning(f"Failed to parse match {match}: {e}")
                continue
        return transactions


def validate_transaction(trans: Transaction) -> bool:
    """对交易记录进行简单校验。"""
    if not trans.bank:
        logger.warning(f"Invalid transaction: Bank is required - {trans}")
        return False
    if not trans.date:
        logger.warning(f"Invalid transaction: Date is required - {trans}")
        return False
    if not isinstance(trans.amount, (int, float)):
        logger.warning(f"Invalid transaction: Amount must be numeric - {trans}")
        return False
    return True


def save_transactions(
    transactions: List[Transaction], output_file: Optional[Path] = None
) -> None:
    """将交易记录保存为 CSV 文件，日期格式为 mm/dd/yyyy。"""
    if not transactions:
        logger.warning("No transactions to save.")
        return

    output_file = output_file or (
        Config.OUTPUT_DIR / f"transactions_{datetime.now():%Y%m%d}.csv"
    )

    try:
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Bank", "Date", "Amount", "Description", "Category"])
            valid_count = 0
            for trans in transactions:
                if validate_transaction(trans):
                    date_str = trans.date.strftime("%m/%d/%Y")
                    writer.writerow(
                        [
                            trans.bank,
                            date_str,
                            trans.amount,
                            trans.description,
                            trans.category,
                        ]
                    )
                    valid_count += 1
        logger.info(f"Saved {valid_count} valid transactions to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save transactions: {e}")
        raise


def load_bank_regex_config() -> dict:
    """加载 bank_data_regex.yaml 配置文件。"""
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
    通过在文本中搜索银行名称关键字，尝试检测 PDF 属于哪个银行。
    """
    text_lower = text.lower()
    for bank_name in bank_regex_data.keys():
        if bank_name.lower() in text_lower:
            return bank_name
    return None


def get_bank_processor(
    pdf_file: Path, bank_regex_data: dict
) -> Optional[GenericBankProcessor]:
    """
    根据 PDF 文本内容返回 GenericBankProcessor，如果无法识别银行则返回 None。
    """
    text = PdfTextExtractor._extract_text_from_pdf(pdf_file)
    bank_name = detect_bank(text, bank_regex_data)
    if not bank_name:
        return None
    bank_config = bank_regex_data[bank_name]
    return GenericBankProcessor(bank_name, bank_config)


def is_leap_year(year: int) -> bool:
    """判断是否为闰年"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


# ------------------------------------------------------------------------------
# 4. 并行处理 PDF 的函数（多进程模式）
# ------------------------------------------------------------------------------
def process_single_pdf(pdf_file: Path, bank_regex_data: dict) -> List[Transaction]:
    """
    处理单个 PDF 文件，返回解析到的交易记录列表。
    此函数适合在多进程环境中调用。
    """
    logger.info(f"Processing PDF: {pdf_file.name}")
    try:
        processor = get_bank_processor(pdf_file, bank_regex_data)
        if processor:
            return processor.process_pdf(pdf_file)
        else:
            logger.warning(f"Unrecognized bank for {pdf_file.name}")
            return []
    except Exception as e:
        logger.error(f"Failed to process {pdf_file.name}: {e}")
        return []


# ------------------------------------------------------------------------------
# 5. 程序入口：使用多进程并行处理 PDF
# ------------------------------------------------------------------------------
def main():
    Config.ensure_dirs()
    bank_regex_data = load_bank_regex_config()
    if not bank_regex_data:
        logger.warning("No bank regex data available, cannot process.")
        return

    pdf_files = list(Config.PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {Config.PDF_DIR}")
        return

    all_transactions: List[Transaction] = []
    # 使用 ProcessPoolExecutor 并行处理 PDF 文件
    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_to_pdf = {
            executor.submit(process_single_pdf, pdf_file, bank_regex_data): pdf_file
            for pdf_file in pdf_files
        }
        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf_file = future_to_pdf[future]
            try:
                transactions = future.result()
                all_transactions.extend(transactions)
            except Exception as exc:
                logger.error(f"PDF {pdf_file.name} generated an exception: {exc}")

    if all_transactions:
        save_transactions(all_transactions)
    else:
        logger.warning("No transactions were processed.")


def test_single_pdf(pdf_path: str):
    """调试函数，用于单个 PDF 文件的测试。"""
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
        # 如需调试单个 PDF，可取消下面代码注释：
        # test_single_pdf("data/statements/Yourfile.pdf")
    except Exception as e:
        logger.error(f"Program failed: {e}")
        raise
