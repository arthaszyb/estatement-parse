# E-Statement Parser

A secure, offline tool to transform bank statement PDFs into structured CSV data for personal finance analysis.

## Key Features

- 🔒 100% offline processing for data privacy
- 📊 Export to standard CSV format for Excel/Sheets analysis
- 🏦 Support for major Singapore banks:
  - Standard Chartered
  - UOB
  - Trust Bank
  - Citibank
- 🔄 Extensible design for adding new bank formats
- 📈 Enable personal finance analysis with your preferred tools

## Why Use This Tool?

- **Privacy First**: All processing happens locally on your machine
- **Data Ownership**: Export to standard CSV format you control
- **Flexible Analysis**: Use with any spreadsheet tool for charts and pivot tables
- **Easy Extension**: Simple regex-based format for adding new bank support

## Installation

```bash
# Clone repository
git clone https://github.com/arthaszyb/estatement-parse.git
cd estatement-parse

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS

# Install dependencies
pip install -r requirements.txt
```

## Usage

1. Before run the tool, please ensure the statement files are ready in the *data/statements/*

2. To parse a statement, run the following command:

```sh
python parse_statement.py
```

3. You will get the csv file from *data/csv/*

4. Import the csv file to your local Sheet file or online Sheet.

5. Be ready to free analysis your financial data with pivot table and charts as a template.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.