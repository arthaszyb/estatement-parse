import pytest
from pathlib import Path
from datetime import date
import pandas as pd
from src.models.transaction import Transaction
from src.utils.exporters import TransactionExporter
from src.utils.config import Config

@pytest.fixture
def sample_transactions():
    """Create sample transactions for testing"""
    return [
        Transaction(
            bank="TestBank",
            date=date(2024, 1, 1),
            amount=100.50,
            description="AMAZON.COM",
            category="Shopping"
        ),
        Transaction(
            bank="TestBank",
            date=date(2024, 1, 2),
            amount=75.50,
            description="WALMART",
            category="Shopping"
        ),
        Transaction(
            bank="TestBank",
            date=date(2024, 1, 3),
            amount=25.00,
            description="RESTAURANT ABC",
            category="Food"
        )
    ]

def test_csv_export(tmp_path, sample_transactions):
    """Test CSV export"""
    # Set temporary output directory
    Config.OUTPUT_DIR = tmp_path
    
    # Export to CSV
    csv_path = TransactionExporter.to_csv(sample_transactions)
    assert csv_path.exists()
    
    # Verify CSV content
    df = pd.read_csv(csv_path)
    assert len(df) == len(sample_transactions)
    assert list(df.columns) == ['bank', 'date', 'amount', 'description', 'category']

def test_excel_export(tmp_path, sample_transactions):
    """Test Excel export"""
    # Set temporary output directory
    Config.OUTPUT_DIR = tmp_path
    
    # Export to Excel
    excel_path = TransactionExporter.to_excel(sample_transactions)
    assert excel_path.exists()
    
    # Verify Excel content
    df = pd.read_excel(excel_path)
    assert len(df) == len(sample_transactions)
    assert list(df.columns) == ['bank', 'date', 'amount', 'description', 'category']

def test_json_export(tmp_path, sample_transactions):
    """Test JSON export"""
    # Set temporary output directory
    Config.OUTPUT_DIR = tmp_path
    
    # Export to JSON
    json_path = TransactionExporter.to_json(sample_transactions)
    assert json_path.exists()
    
    # Verify JSON content
    df = pd.read_json(json_path)
    assert len(df) == len(sample_transactions)
    assert list(df.columns) == ['bank', 'date', 'amount', 'description', 'category']

def test_empty_transactions(tmp_path):
    """Test exporting empty transaction list"""
    # Set temporary output directory
    Config.OUTPUT_DIR = tmp_path
    
    # Try exporting empty list
    assert TransactionExporter.to_csv([]) is None
    assert TransactionExporter.to_excel([]) is None
    assert TransactionExporter.to_json([]) is None 