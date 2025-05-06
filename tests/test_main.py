import pytest
from pathlib import Path
import shutil
import yaml
from fpdf import FPDF
from src.main import load_bank_config, detect_bank, process_single_pdf
from src.utils.config import Config

@pytest.fixture
def setup_test_env(tmp_path):
    """Setup test environment with sample files"""
    # Create test directories
    test_dirs = {
        'conf': tmp_path / 'conf',
        'data': tmp_path / 'data',
        'statements': tmp_path / 'data' / 'statements',
        'csv': tmp_path / 'data' / 'csv',
        'logs': tmp_path / 'data' / 'logs'
    }
    for dir_path in test_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create test configuration
    config = {
        'banks': {
            'TestBank': {
                'pattern': r'(\d{2}\s[A-Za-z]{3})\s+([A-Za-z0-9\s\.]+?)\s+\$(\d+\.\d{2})',
                'transaction_date_group': 0,
                'description_group': 1,
                'amount_group': 2,
                'cr_group': None,
                'invert_amount_if_cr': False,
                'plus_means_negative': False,
                'parse_date_format': '%d %b'
            }
        }
    }
    
    config_file = test_dirs['conf'] / 'bank_data_regex.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    
    # Create sample PDF statement using FPDF
    statement_file = test_dirs['statements'] / 'test_statement.pdf'
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    sample_text = """
    TestBank STATEMENT
    Account: 1234-5678-9012
    Statement Date: 31 Jan 2024
    
    TRANSACTIONS
    Date        Description                 Amount
    01 Jan     AMAZON.COM                 $50.00
    02 Jan     WALMART                    $75.50
    03 Jan     RESTAURANT ABC             $25.00
    """
    
    for line in sample_text.split('\n'):
        pdf.cell(0, 10, txt=line.strip(), ln=True)
    
    pdf.output(str(statement_file))
    
    # Update Config paths
    Config.CONF_DIR = test_dirs['conf']
    Config.DATA_DIR = test_dirs['data']
    Config.OUTPUT_DIR = test_dirs['csv']
    Config.PDF_DIR = test_dirs['statements']
    Config.LOG_DIR = test_dirs['logs']
    Config.BANK_DATA_REGEX_FILE = str(config_file)
    
    return test_dirs

def test_load_bank_config(setup_test_env):
    """Test loading bank configuration"""
    config = load_bank_config()
    assert 'TestBank' in config
    assert 'pattern' in config['TestBank']
    assert 'transaction_date_group' in config['TestBank']

def test_detect_bank(setup_test_env):
    """Test bank detection from text"""
    text = "This is a TestBank statement"
    bank_config = load_bank_config()
    bank_name = detect_bank(text, bank_config)
    assert bank_name == 'TestBank'
    
    # Test with unknown bank
    text = "This is an unknown bank statement"
    bank_name = detect_bank(text, bank_config)
    assert bank_name is None

def test_process_single_pdf(setup_test_env):
    """Test processing a single PDF file"""
    bank_config = load_bank_config()
    statement_file = Path(setup_test_env['statements']) / 'test_statement.pdf'
    
    # Process the statement
    transactions = process_single_pdf(statement_file, bank_config)
    
    # Verify results
    assert len(transactions) > 0
    for trans in transactions:
        assert trans.bank == 'TestBank'
        assert trans.amount > 0
        assert trans.description
        assert trans.category
        assert trans.date.year == 2024 