"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: utils/helpers.py
Purpose: Helper functions and utilities
Author: v0
Created: 2025
==========================================================================

OVERVIEW:
---------
Collection of helper functions for:
- Safe mathematical operations
- Data formatting
- Date calculations
- Text utilities

USAGE:
------
    from utils.helpers import safe_divide, format_currency
    
    result = safe_divide(100, 0)  # Returns 0 instead of error
    formatted = format_currency(1500000)  # Returns "Rp 1,500,000"
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Any, Optional, Union

import sys
sys.path.append('..')
from config.constants import CURRENCY_CONFIG, DATE_CONFIG


def safe_divide(
    numerator: Union[int, float], 
    denominator: Union[int, float], 
    default: Union[int, float] = 0
) -> float:
    """
    Safely divide two numbers, returning default if division by zero.
    
    Args:
        numerator: The dividend
        denominator: The divisor
        default: Value to return if division by zero
        
    Returns:
        Result of division or default value
        
    Example:
        >>> safe_divide(100, 0)
        0
        >>> safe_divide(100, 4)
        25.0
    """
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return float(numerator) / float(denominator)
    except (TypeError, ValueError):
        return default


def format_currency(
    value: Union[int, float], 
    include_symbol: bool = True,
    decimal_places: int = 0
) -> str:
    """
    Format number as Indonesian Rupiah currency.
    
    Args:
        value: Numeric value to format
        include_symbol: Whether to include "Rp" prefix
        decimal_places: Number of decimal places
        
    Returns:
        Formatted currency string
        
    Example:
        >>> format_currency(1500000)
        'Rp 1,500,000'
        >>> format_currency(1500000.50, decimal_places=2)
        'Rp 1,500,000.50'
    """
    try:
        if pd.isna(value):
            return "Rp 0" if include_symbol else "0"
        
        value = float(value)
        
        if decimal_places > 0:
            formatted = f"{value:,.{decimal_places}f}"
        else:
            formatted = f"{value:,.0f}"
        
        if include_symbol:
            return f"{CURRENCY_CONFIG['CURRENCY_SYMBOL']} {formatted}"
        return formatted
        
    except (TypeError, ValueError):
        return "Rp 0" if include_symbol else "0"


def format_percentage(
    value: Union[int, float], 
    decimal_places: int = 1,
    multiply: bool = False
) -> str:
    """
    Format number as percentage string.
    
    Args:
        value: Numeric value (0-100 or 0-1)
        decimal_places: Number of decimal places
        multiply: If True, multiply by 100 first
        
    Returns:
        Formatted percentage string
        
    Example:
        >>> format_percentage(0.942, multiply=True)
        '94.2%'
        >>> format_percentage(94.2)
        '94.2%'
    """
    try:
        if pd.isna(value):
            return "0%"
        
        value = float(value)
        
        if multiply:
            value *= 100
        
        return f"{value:.{decimal_places}f}%"
        
    except (TypeError, ValueError):
        return "0%"


def format_number(
    value: Union[int, float],
    decimal_places: int = 0,
    use_thousands: bool = True
) -> str:
    """
    Format number with thousands separator.
    
    Args:
        value: Numeric value
        decimal_places: Number of decimal places
        use_thousands: Whether to use thousands separator
        
    Returns:
        Formatted number string
        
    Example:
        >>> format_number(1234567)
        '1,234,567'
    """
    try:
        if pd.isna(value):
            return "0"
        
        value = float(value)
        
        if use_thousands:
            if decimal_places > 0:
                return f"{value:,.{decimal_places}f}"
            return f"{value:,.0f}"
        else:
            if decimal_places > 0:
                return f"{value:.{decimal_places}f}"
            return f"{value:.0f}"
            
    except (TypeError, ValueError):
        return "0"


def format_large_number(value: Union[int, float]) -> str:
    """
    Format large numbers with K, M, B suffixes.
    
    Args:
        value: Numeric value
        
    Returns:
        Formatted string with suffix
        
    Example:
        >>> format_large_number(1500000)
        '1.5M'
        >>> format_large_number(1234)
        '1.2K'
    """
    try:
        if pd.isna(value):
            return "0"
        
        value = float(value)
        
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:.0f}"
            
    except (TypeError, ValueError):
        return "0"


def calculate_days_ago(date_value: Any) -> int:
    """
    Calculate number of days from a date to today.
    
    Args:
        date_value: Date value (datetime, string, or timestamp)
        
    Returns:
        Number of days (integer)
    """
    try:
        if pd.isna(date_value):
            return 9999
        
        if isinstance(date_value, str):
            date_value = pd.to_datetime(date_value)
        
        delta = datetime.now() - pd.Timestamp(date_value)
        return max(0, delta.days)
        
    except Exception:
        return 9999


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
        
    Example:
        >>> truncate_text("This is a very long product name", 20)
        'This is a very lo...'
    """
    if pd.isna(text):
        return ""
    
    text = str(text)
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_date(
    date_str: str, 
    format_str: Optional[str] = None
) -> Optional[datetime]:
    """
    Parse date string to datetime object.
    
    Args:
        date_str: Date string to parse
        format_str: Format string (default from config)
        
    Returns:
        datetime object or None if parsing fails
    """
    if pd.isna(date_str):
        return None
    
    if format_str is None:
        format_str = DATE_CONFIG['DATE_FORMAT']
    
    try:
        return datetime.strptime(str(date_str), format_str)
    except ValueError:
        try:
            return pd.to_datetime(date_str)
        except Exception:
            return None


def get_date_range_description(start_date: str, end_date: str) -> str:
    """
    Get human-readable date range description.
    
    Args:
        start_date: Start date string
        end_date: End date string
        
    Returns:
        Description string
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        if start and end:
            days = (end - start).days
            if days <= 30:
                return f"{days} days"
            elif days <= 90:
                return f"{days // 7} weeks"
            elif days <= 365:
                return f"{days // 30} months"
            else:
                return f"{days // 365} years"
    except Exception:
        pass
    
    return f"{start_date} to {end_date}"
