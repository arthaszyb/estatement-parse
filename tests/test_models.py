import pytest
from datetime import date
from src.models.transaction import Transaction

def test_transaction_creation():
    """Test creating a Transaction object"""
    trans = Transaction(
        bank="TestBank",
        date=date(2024, 1, 1),
        amount=100.50,
        description="AMAZON.COM",
        category="Shopping"
    )
    
    assert trans.bank == "TestBank"
    assert trans.date == date(2024, 1, 1)
    assert trans.amount == 100.50
    assert trans.description == "AMAZON.COM"
    assert trans.category == "Shopping"

def test_transaction_validation():
    """Test transaction validation"""
    # Valid transaction
    trans = Transaction(
        bank="TestBank",
        date=date(2024, 1, 1),
        amount=100.50,
        description="AMAZON.COM",
        category="Shopping"
    )
    assert trans.bank is not None
    assert trans.date is not None
    assert isinstance(trans.amount, (int, float))
    
    # Invalid amount
    with pytest.raises(TypeError):
        Transaction(
            bank="TestBank",
            date=date(2024, 1, 1),
            amount="100.50",  # Should be float
            description="AMAZON.COM",
            category="Shopping"
        ) 