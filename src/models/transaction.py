from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class Transaction:
    """
    Represents a bank transaction record.
    
    Attributes:
        bank (str): Name of the bank
        date (date): Transaction date
        amount (float): Transaction amount
        description (str): Transaction description
        category (str): Transaction category
        
    Example:
        >>> trans = Transaction(
        ...     bank="Chase",
        ...     date=date(2024, 1, 1),
        ...     amount=100.50,
        ...     description="AMAZON.COM",
        ...     category="Shopping"
        ... )
    """
    bank: str
    date: date
    amount: float
    description: str
    category: str
    
    def __post_init__(self):
        """Validate types after initialization"""
        if not isinstance(self.bank, str):
            raise TypeError(f"bank must be str, not {type(self.bank)}")
        if not isinstance(self.date, date):
            raise TypeError(f"date must be date, not {type(self.date)}")
        if not isinstance(self.amount, (int, float)):
            raise TypeError(f"amount must be numeric, not {type(self.amount)}")
        if not isinstance(self.description, str):
            raise TypeError(f"description must be str, not {type(self.description)}")
        if not isinstance(self.category, str):
            raise TypeError(f"category must be str, not {type(self.category)}") 