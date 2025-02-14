# E-Statement Parser

**E-Statement Parser** is a secure, offline tool that converts bank statement PDFs into structured CSV data—making your personal finance analysis easier than ever.

---

## Key Features

- 🔒 **100% Offline Processing:** All operations run locally for maximum data privacy.
- 📊 **CSV Export:** Easily generate CSV files compatible with Excel, Google Sheets, or any other spreadsheet tool.
- 🏦 **Supports Major Singapore Banks:**
  - Standard Chartered
  - UOB
  - Trust Bank
  - Citibank
- 🔄 **Extensible Architecture:** Add support for new bank formats effortlessly using regex-based configurations.
- 📈 **Empower Your Analysis:** Prepare your data for in-depth analysis with pivot tables, charts, and more.

---

## Why Choose E-Statement Parser?

- **Privacy First:** Your sensitive financial data never leaves your computer.
- **Data Ownership:** You control your data with standard CSV exports.
- **Flexible Analysis:** Work with your favorite spreadsheet or BI tools.
- **Easy Customization:** Extend support to additional bank formats with simple regex configurations.

---

## Installation

Follow these steps to set up the tool:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/arthaszyb/estatement-parse.git
   cd estatement-parse
   ```

2. **Create and Activate a Virtual Environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # For macOS/Linux
   # On Windows, use: .venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

1. **Prepare Your PDF Files:**

   - Place your bank statement PDF files in the `data/statements/` directory.

2. **Run the Parser:**

   ```bash
   python parse_statement.py
   ```

3. **Review the Output:**

   - The resulting CSV file(s) will be saved in the `data/csv/` directory.

4. **Analyze Your Data:**

   - Import the CSV file into your preferred spreadsheet or data analysis tool to create charts, pivot tables, and more.

---

## Contributing

Contributions are welcome! If you have ideas for improvements or new bank formats to support, please:

- Open an issue to discuss your ideas.
- Submit a pull request with your enhancements.

---

## License

This project is licensed under the [MIT License](LICENSE).