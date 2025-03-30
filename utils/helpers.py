"""
Helper utilities for stock analysis application.
"""
import os
import re
import json
import datetime
from typing import Dict, List, Optional, Union, Any

import pandas as pd
from loguru import logger


def is_market_open() -> bool:
    """
    Check if the market is currently open.

    Returns:
        bool: True if market is open, False otherwise
    """
    from config.settings import (
        MARKET_OPEN_HOUR,
        MARKET_OPEN_MINUTE,
        MARKET_CLOSE_HOUR,
        MARKET_CLOSE_MINUTE
    )

    now = datetime.datetime.now()

    # Check if it's a weekday (0 = Monday, 6 = Sunday)
    if now.weekday() > 4:  # Saturday or Sunday
        return False

    # Check if it's within market hours
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)

    return market_open <= now <= market_close


def format_currency(value: Union[float, int]) -> str:
    """
    Format value as currency.

    Args:
        value: Numeric value to format

    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"

    return f"₹{value:,.2f}"


def format_percentage(value: float) -> str:
    """
    Format value as percentage.

    Args:
        value: Percentage value to format

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"

    return f"{value:.2f}%"


def format_number(value: Union[float, int], decimals: int = 2) -> str:
    """
    Format numeric value with specified decimals.

    Args:
        value: Numeric value to format
        decimals: Number of decimal places

    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"

    format_string = f"{{:,.{decimals}f}}"
    return format_string.format(value)


def safe_divide(numerator: Union[float, int], denominator: Union[float, int]) -> Optional[float]:
    """
    Safely divide numbers, avoiding division by zero.

    Args:
        numerator: Division numerator
        denominator: Division denominator

    Returns:
        Division result or None if denominator is zero
    """
    if denominator == 0:
        return None

    return numerator / denominator


def generate_option_symbol(symbol: str, expiry: str, strike: float, option_type: str) -> str:
    """
    Generate option symbol based on standard format.

    Args:
        symbol: Stock symbol
        expiry: Expiry month (e.g., 'APR')
        strike: Strike price
        option_type: Option type (CE/PE)

    Returns:
        Formatted option symbol
    """
    # Format strike without decimal if it's a whole number
    strike_str = str(int(strike)) if strike.is_integer() else str(strike)

    # Construct the full symbol
    full_symbol = f"{symbol}{expiry}{strike_str}{option_type}"

    return full_symbol


def read_json_file(file_path: str) -> Dict[str, Any]:
    """
    Read and parse JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON content as dictionary
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {str(e)}")
        return {}


def write_json_file(data: Dict[str, Any], file_path: str) -> bool:
    """
    Write dictionary to JSON file.

    Args:
        data: Dictionary to write
        file_path: Output file path

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        return True
    except Exception as e:
        logger.error(f"Error writing JSON file {file_path}: {str(e)}")
        return False


def read_csv_file(file_path: str) -> Optional[pd.DataFrame]:
    """
    Read CSV file into DataFrame.

    Args:
        file_path: Path to CSV file

    Returns:
        DataFrame with CSV content or None if error
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {str(e)}")
        return None


def write_csv_file(df: pd.DataFrame, file_path: str) -> bool:
    """
    Write DataFrame to CSV file.

    Args:
        df: DataFrame to write
        file_path: Output file path

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        logger.error(f"Error writing CSV file {file_path}: {str(e)}")
        return False


def get_timestamp() -> str:
    """
    Get current timestamp string.

    Returns:
        Formatted timestamp string
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_date(date_str: str) -> Optional[datetime.datetime]:
    """
    Parse date string into datetime object.

    Args:
        date_str: Date string to parse

    Returns:
        Datetime object or None if parsing fails
    """
    date_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    ]

    for fmt in date_formats:
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.error(f"Could not parse date string: {date_str}")
    return None