"""
Input validation utilities for stock analysis application.
"""
import re
from typing import List, Optional, Union, Dict, Any

from loguru import logger


def validate_symbol(symbol: str) -> bool:
    """
    Validate stock symbol format.

    Args:
        symbol: Stock symbol to validate

    Returns:
        True if valid, False otherwise
    """
    if not symbol:
        return False

    # Basic validation for Indian stock symbols
    # Most NSE symbols are 2-20 alphanumeric characters
    pattern = re.compile(r'^[A-Z0-9]{2,20}$')

    return bool(pattern.match(symbol))


def validate_symbols_list(symbols: List[str]) -> List[str]:
    """
    Validate list of stock symbols and return only valid ones.

    Args:
        symbols: List of stock symbols to validate

    Returns:
        List of valid symbols
    """
    if not symbols:
        return []

    valid_symbols = [symbol for symbol in symbols if validate_symbol(symbol)]

    if len(valid_symbols) < len(symbols):
        invalid_count = len(symbols) - len(valid_symbols)
        logger.warning(f"{invalid_count} invalid symbols removed from input list")

    return valid_symbols


def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Validate date range for historical data.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        True if valid, False otherwise
    """
    # Basic date format validation
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    if not date_pattern.match(start_date) or not date_pattern.match(end_date):
        return False

    # Check if start_date is before end_date
    return start_date <= end_date


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False

    # Typical API key pattern (alphanumeric with specific length)
    # Adjust based on actual Zerodha API key format
    pattern = re.compile(r'^[A-Za-z0-9]{16}$')

    return bool(pattern.match(api_key))


def validate_numeric_range(value: Union[int, float], min_val: Union[int, float],
                           max_val: Union[int, float]) -> bool:
    """
    Validate if a numeric value is within specified range.

    Args:
        value: Numeric value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        True if valid, False otherwise
    """
    if value is None:
        return False

    return min_val <= value <= max_val


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate JSON data against a schema.

    Args:
        data: JSON data to validate
        schema: Schema definition

    Returns:
        True if valid, False otherwise
    """
    # Basic schema validation (simplified)
    # In a real implementation, use a library like jsonschema

    try:
        # Check required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    logger.error(f"Required field missing: {field}")
                    return False

        # Check field types
        if "properties" in schema:
            for field, field_schema in schema["properties"].items():
                if field in data and data[field] is not None:
                    # Check type
                    if "type" in field_schema:
                        type_map = {
                            "string": str,
                            "integer": int,
                            "number": (int, float),
                            "boolean": bool,
                            "array": list,
                            "object": dict
                        }

                        expected_type = type_map.get(field_schema["type"])
                        if expected_type and not isinstance(data[field], expected_type):
                            logger.error(f"Invalid type for field {field}")
                            return False

        return True
    except Exception as e:
        logger.error(f"Schema validation error: {str(e)}")
        return False


def sanitize_input(value: str) -> str:
    """
    Sanitize input string to prevent injection attacks.

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string
    """
    if not value:
        return ""

    # Remove potential script tags and other dangerous content
    value = re.sub(r'<script.*?>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r'<.*?>', '', value)

    # Escape special characters
    value = (value
             .replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;')
             .replace("'", '&#x27;')
             )

    return value