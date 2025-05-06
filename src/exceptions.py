class BankStatementError(Exception):
    """Base exception for bank statement processing"""
    pass

class ConfigError(BankStatementError):
    """Configuration related errors"""
    pass

class PDFParseError(BankStatementError):
    """PDF parsing related errors"""
    pass

class TransactionParseError(BankStatementError):
    """Transaction parsing related errors"""
    pass

class ValidationError(BankStatementError):
    """Data validation errors"""
    pass 