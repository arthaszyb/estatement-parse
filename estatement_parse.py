import io
import pdfminer.converter
import pdfminer.pdfinterp
import pdfminer.layout
import pdfminer.pdfparser
import pdfminer.pdfdocument
import pdfminer.pdfpage
import re
import csv
import glob
from abc import ABC, abstractmethod
from collections import namedtuple
import yaml
from pdfminer.layout import LAParams
import pdfplumber

# 定义具名元组
Transaction = namedtuple("Transaction", ["bank", "date", "amount", "description", "category"])

category_mapping_file = "conf/category_mapping.yaml"


class PdfTextExtractor:
    """MixIn类， PDF文本提取"""

    @staticmethod
    def _extract_text_from_pdf(pdf_path):
        """从PDF文件中提取文本内容。"""
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


def main():
    """主程序：处理PDF文件并输出到CSV。"""
    # 银行处理器实例
    bank_processors = {
        "Standard Chartered": StandardCharteredProcessor(),
        "UOB": UOBProcessor(),
        "Citibank": CitibankProcessor(),
        "Trust": TrustProcessor()
    }

    all_transactions = []
    pdf_files = glob.glob("data/statements/*.pdf")  # 获取当前目录下所有PDF文件

    for pdf_file in pdf_files:
        text = PdfTextExtractor._extract_text_from_pdf(pdf_file)
        print(f"Extracted text from {pdf_file}:")
        #print(text[:5000])  # 打印前5000个字符用于调试
        
        bank = None
        for bank_name in bank_processors:
            if bank_name.lower() in text.lower():
                bank = bank_name
                break

        if bank:
            print(f"使用 {bank} 的逻辑处理 {pdf_file}")
            processor = bank_processors[bank]
            transactions = processor.process_pdf(pdf_file)
            all_transactions.extend(transactions)
        else:
            print(f"无法识别 {pdf_file} 的银行类型")

    # 输出到CSV
    with open("data/csv/transactions.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Bank", "Date", "Amount", "Description", "Category"])
        for trans in all_transactions:
            writer.writerow([trans.bank, trans.date, trans.amount, trans.description, trans.category])

    print("交易记录已保存到 transactions.csv")

   


if __name__ == "__main__":
    main()