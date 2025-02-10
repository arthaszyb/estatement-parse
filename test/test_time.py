from datetime import datetime
import logging

def parse_date(date_str: str, fmt: str) -> datetime.date:
    """Convert date_str using the given format into a date object.
       If date_str includes a year but fmt doesn't expect it, adjust the format.
    """
    stripped = date_str.strip()
    # Detect if a 4-digit year is present.
    has_year = any(token.isdigit() and len(token) == 4 for token in stripped.split())
    
    # If a year is present in date_str but not in fmt, update the format.
    if has_year and '%Y' not in fmt:
        fmt = fmt + " %Y"
    
    try:
        dt = datetime.strptime(stripped, fmt)
        # If the format still doesn't include a year, use the current year.
        if '%Y' not in fmt:
            dt = dt.replace(year=datetime.now().year)
        return dt.date()
    except ValueError:
        logging.warning(f"Cannot parse date string: '{date_str}' with format '{fmt}'")
        return None

if __name__ == "__main__":
    # Test cases:
    print(parse_date("12 Jan", "%d %b"))         # Uses current year
    print(parse_date("12 Jan 2025", "%d %b"))      # Adjusts to "%d %b %Y"
    print(parse_date("12 Jan 2024", "%d %b %Y"))    # Works as expected