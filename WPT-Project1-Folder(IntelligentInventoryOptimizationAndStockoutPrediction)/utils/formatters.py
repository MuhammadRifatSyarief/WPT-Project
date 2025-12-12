"""
Data Formatting & Display Module
==================================

Modul ini berisi formatter functions untuk display values
dalam berbagai format (currency, percentage, date, etc).

Author: Data Science Team
Date: 2025-11-18
Version: 1.0
"""

import pandas as pd
from datetime import datetime


def format_currency(value, currency_symbol: str = 'Rp ', decimals: int = 0) -> str:
    """
    Format nilai sebagai currency.
    
    Args:
        value: Nilai numeric
        currency_symbol (str): Currency symbol (default: Rp)
        decimals (int): Decimal places
        
    Returns:
        str: Formatted currency string
        
    Example:
        >>> format_currency(1500000)
        'Rp 1,500,000'
        >>> format_currency(1500.5, '$', 2)
        '$ 1,500.50'
    """
    
    if pd.isna(value):
        return f'{currency_symbol}0'
    
    try:
        value = float(value)
        formatted = f"{value:,.{decimals}f}"
        return f"{currency_symbol}{formatted}"
    except:
        return f'{currency_symbol}0'


def format_percentage(value, decimals: int = 1) -> str:
    """
    Format nilai sebagai percentage.
    
    Args:
        value: Nilai (0-100 atau 0-1)
        decimals (int): Decimal places
        
    Returns:
        str: Formatted percentage string
        
    Example:
        >>> format_percentage(0.942)
        '94.2%'
        >>> format_percentage(94.2, 0)
        '94%'
    """
    
    if pd.isna(value):
        return '0%'
    
    try:
        value = float(value)
        # Convert 0-1 range to 0-100 jika diperlukan
        if value <= 1:
            value = value * 100
        return f"{value:.{decimals}f}%"
    except:
        return '0%'


def format_number(value, decimals: int = 2, use_separators: bool = True) -> str:
    """
    Format nilai sebagai general number.
    
    Args:
        value: Nilai numeric
        decimals (int): Decimal places
        use_separators (bool): Gunakan thousand separators
        
    Returns:
        str: Formatted number string
        
    Example:
        >>> format_number(1234567.89)
        '1,234,567.89'
        >>> format_number(1234567.89, 0)
        '1,234,568'
    """
    
    if pd.isna(value):
        return '0'
    
    try:
        value = float(value)
        if use_separators:
            return f"{value:,.{decimals}f}"
        else:
            return f"{value:.{decimals}f}"
    except:
        return '0'


def format_date(date_input, format_str: str = '%d-%m-%Y') -> str:
    """
    Format date ke string format tertentu.
    
    Args:
        date_input: Date (datetime atau string)
        format_str (str): Format string (default: DD-MM-YYYY)
        
    Returns:
        str: Formatted date string
        
    Example:
        >>> format_date(datetime.now())
        '18-11-2025'
        >>> format_date('2025-11-18', '%d %B %Y')
        '18 November 2025'
    """
    
    if pd.isna(date_input):
        return 'N/A'
    
    try:
        if isinstance(date_input, str):
            date_input = datetime.strptime(date_input, '%Y-%m-%d')
        
        if isinstance(date_input, datetime):
            return date_input.strftime(format_str)
        
        return str(date_input)
    except:
        return str(date_input)


def format_time(time_input, format_str: str = '%H:%M:%S') -> str:
    """
    Format time ke string format tertentu.
    
    Args:
        time_input: Time (datetime atau string)
        format_str (str): Format string (default: HH:MM:SS)
        
    Returns:
        str: Formatted time string
        
    Example:
        >>> format_time(datetime.now())
        '14:30:45'
    """
    
    if pd.isna(time_input):
        return 'N/A'
    
    try:
        if isinstance(time_input, str):
            time_input = datetime.strptime(time_input, '%H:%M:%S')
        
        if isinstance(time_input, datetime):
            return time_input.strftime(format_str)
        
        return str(time_input)
    except:
        return str(time_input)


def format_duration(seconds: int) -> str:
    """
    Format durasi dari seconds menjadi readable format.
    
    Args:
        seconds (int): Total seconds
        
    Returns:
        str: Formatted duration (e.g., "1d 2h 30m")
        
    Example:
        >>> format_duration(3665)
        '1h 1m'
        >>> format_duration(86400)
        '1d'
    """
    
    if seconds < 0:
        return '0s'
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or len(parts) == 0:
        parts.append(f"{secs}s")
    
    return ' '.join(parts)


def format_status_badge(status: str) -> str:
    """
    Format status sebagai badge dengan warna.
    
    Args:
        status (str): Status value
        
    Returns:
        str: HTML formatted badge
        
    Example:
        >>> format_status_badge('Active')
        '<span style="...">Active</span>'
    """
    
    color_map = {
        'Active': '#10b981',
        'Inactive': '#94a3b8',
        'Critical': '#ef4444',
        'Warning': '#f59e0b',
        'Good': '#10b981'
    }
    
    color = color_map.get(status, '#6366f1')
    
    return f"""
    <span style="
        background: {color};
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
    ">
        {status}
    </span>
    """


def format_large_number(value, decimals: int = 1) -> str:
    """
    Format large numbers ke shortened format (K, M, B).
    
    Args:
        value: Nilai numeric
        decimals (int): Decimal places untuk suffix
        
    Returns:
        str: Formatted number (e.g., "1.5M", "500K")
        
    Example:
        >>> format_large_number(1500000)
        '1.5M'
        >>> format_large_number(500000)
        '500K'
    """
    
    if pd.isna(value):
        return '0'
    
    try:
        value = float(value)
        
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:.{decimals}f}B"
        elif abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.{decimals}f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.{decimals}f}K"
        else:
            return f"{value:.{decimals}f}"
    except:
        return '0'
