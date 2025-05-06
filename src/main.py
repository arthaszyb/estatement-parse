import logging
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional
from .utils.config import Config
from .utils.logging import LogManager
from .utils.validators import InputValidator
from .processors.generic import GenericBankProcessor
from .models.transaction import Transaction
from .utils.exporters import TransactionExporter

logger = logging.getLogger(__name__)

def load_bank_config() -> Dict[str, Any]:
    """Load bank configuration from YAML file"""
    try:
        return Config.load_yaml(Config.BANK_DATA_REGEX_FILE).get("banks", {})
    except Exception as e:
        logger.error(f"Failed to load bank configuration: {e}")
        return {}

def detect_bank(text: str, bank_config: Dict[str, Any]) -> Optional[str]:
    """Detect bank from PDF text content"""
    text_lower = text.lower()
    
    # First try exact matches
    for bank_name in bank_config.keys():
        if bank_name.lower() in text_lower:
            return bank_name
            
    # Then try partial matches and common variations
    bank_variations = {
        'Standard Chartered': ['standard chartered', 'stanchart', 'scb', 'standard chartered bank'],
        'UOB': ['united overseas bank', 'uob', 'united overseas'],
        'Citibank': ['citibank', 'citi', 'citigroup'],
        'HSBC': ['hsbc', 'hongkong and shanghai banking corporation', 'hongkong', 'hong kong', 'hsbc bank'],
    }
    
    # Check for bank name in filename
    for bank_name, variations in bank_variations.items():
        if bank_name in bank_config:
            # Check if any variation is in the text
            if any(var in text_lower for var in variations):
                return bank_name
                
            # Check if bank name is in the filename (if available)
            if 'filename' in text_lower and bank_name.lower() in text_lower:
                return bank_name
                
    # Try to extract bank name from filename if it contains "Statement" or "eStatement"
    if 'statement' in text_lower or 'estatement' in text_lower:
        for bank_name in bank_config.keys():
            if bank_name.lower() in text_lower:
                return bank_name
                
    return None

def process_single_pdf(pdf_path: Path, bank_config: Dict[str, Any]) -> List[Transaction]:
    """Process a single PDF file"""
    try:
        # Validate PDF path
        pdf_path = InputValidator.validate_pdf_path(pdf_path)
        
        # Extract text and detect bank
        processor = GenericBankProcessor("unknown", {})
        text = processor._extract_text_from_pdf(pdf_path)
        bank_name = detect_bank(text, bank_config)
        
        # If bank detection failed, try to extract from filename
        if not bank_name:
            filename = pdf_path.name.lower()
            logger.warning(f"Could not detect bank for {pdf_path.name}, trying to extract from filename")
            
            # Check if filename contains bank names
            for bank in bank_config.keys():
                if bank.lower() in filename:
                    bank_name = bank
                    logger.info(f"Detected bank '{bank_name}' from filename")
                    break
                    
            # If still not found, try common variations
            if not bank_name:
                bank_variations = {
                    'Standard Chartered': ['standard chartered', 'stanchart', 'scb'],
                    'UOB': ['united overseas bank', 'uob'],
                    'Citibank': ['citibank', 'citi'],
                    'HSBC': ['hsbc', 'hongkong'],
                }
                
                for bank, variations in bank_variations.items():
                    if bank in bank_config and any(var in filename for var in variations):
                        bank_name = bank
                        logger.info(f"Detected bank '{bank_name}' from filename variations")
                        break
        
        if not bank_name:
            logger.warning(f"Could not detect bank for {pdf_path.name}")
            return []
            
        # Process with bank-specific configuration
        processor = GenericBankProcessor(bank_name, bank_config[bank_name])
        return processor.process_pdf(pdf_path)
        
    except Exception as e:
        logger.error(f"Failed to process {pdf_path.name}: {e}")
        return []

def main():
    """Main application entry point"""
    try:
        # Setup logging
        LogManager.setup_logging()
        logger.info("Starting bank statement processing")
        
        # Ensure directories exist
        Config.ensure_dirs()
        
        # Load bank configuration
        bank_config = load_bank_config()
        if not bank_config:
            logger.error("No bank configuration available")
            return
            
        # Get PDF files
        pdf_files = list(Config.PDF_DIR.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"No PDF files found in {Config.PDF_DIR}")
            return
            
        # Process PDFs in parallel
        all_transactions: List[Transaction] = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            future_to_pdf = {
                executor.submit(process_single_pdf, pdf_file, bank_config): pdf_file
                for pdf_file in pdf_files
            }
            
            for future in concurrent.futures.as_completed(future_to_pdf):
                pdf_file = future_to_pdf[future]
                try:
                    transactions = future.result()
                    all_transactions.extend(transactions)
                except Exception as e:
                    logger.error(f"Failed to process {pdf_file.name}: {e}")
        
        # Export transactions
        if all_transactions:
            # Export to multiple formats
            TransactionExporter.to_csv(all_transactions)
            TransactionExporter.to_excel(all_transactions)
            TransactionExporter.to_json(all_transactions)
            logger.info(f"Successfully processed {len(all_transactions)} transactions")
        else:
            logger.warning("No transactions were processed")
            
    except Exception as e:
        logger.error(f"Application failed: {e}")
        raise

if __name__ == "__main__":
    main() 