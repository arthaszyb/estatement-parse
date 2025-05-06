# Bank Statement Parser

A Python application for parsing and processing bank statements from PDF files.

## Features

- PDF text extraction and parsing
- Support for multiple bank statement formats
- Parallel processing of multiple PDFs
- Transaction categorization
- Multiple export formats (CSV, Excel, JSON)
- Comprehensive logging
- Input validation and error handling

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/estatement-parse.git
cd estatement-parse
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Place your bank statement PDFs in the `data/statements` directory.

2. Configure bank-specific regex patterns in `conf/bank_data_regex.yaml`:
```yaml
banks:
  BankName:
    pattern: "regex pattern"
    transaction_date_group: 1
    description_group: 2
    amount_group: 3
    cr_group: 4
    invert_amount_if_cr: true
    plus_means_negative: false
    parse_date_format: "%d %b"
```

3. Configure transaction categories in `conf/category_mapping.yaml`:
```yaml
categories:
  Shopping:
    - AMAZON
    - WALMART
  Food:
    - RESTAURANT
    - GROCERY
```

## Usage

Run the application:
```bash
python -m src.main
```

The processed transactions will be exported to:
- `data/csv/transactions_YYYYMMDD.csv`
- `data/csv/transactions_YYYYMMDD.xlsx`
- `data/csv/transactions_YYYYMMDD.json`

## Project Structure

```
estatement-parse/
├── src/
│   ├── processors/      # Bank statement processors
│   ├── models/          # Data models
│   ├── utils/           # Utility functions
│   └── main.py         # Application entry point
├── tests/              # Test files
├── conf/               # Configuration files
├── data/               # Data directories
│   ├── csv/           # Exported transactions
│   ├── statements/    # Input PDF files
│   └── logs/          # Application logs
└── requirements.txt    # Dependencies
```

## Logging

Logs are written to:
- Console (INFO level)
- `data/logs/app.log` (DEBUG level)

## Error Handling

The application includes comprehensive error handling for:
- PDF parsing errors
- Transaction parsing errors
- Configuration errors
- Input validation errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.