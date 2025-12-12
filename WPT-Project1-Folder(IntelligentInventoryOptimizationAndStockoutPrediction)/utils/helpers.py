"""
Helper Functions Utility Module
================================

Modul ini berisi berbagai helper functions untuk operasi umum
yang digunakan di berbagai modul dan pages.

Author: Data Science Team
Date: 2025-11-18
Version: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def safe_divide(numerator, denominator, default: float = 0.0) -> float:
    """
    Safe division dengan default value jika denominator adalah 0.
    
    Args:
        numerator: Nilai pembilang
        denominator: Nilai penyebut
        default (float): Default value jika denominator == 0
        
    Returns:
        float: Hasil pembagian atau default value
        
    Example:
        >>> safe_divide(100, 0, 0)
        0.0
        >>> safe_divide(100, 50, 0)
        2.0
    """
    
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return float(numerator) / float(denominator)
    except:
        return default


def calculate_percentage(value, total, decimals: int = 1) -> float:
    """
    Calculate persentase dengan safety check.
    
    Args:
        value: Nilai
        total: Total value
        decimals (int): Desimal places
        
    Returns:
        float: Persentase (0-100)
        
    Example:
        >>> calculate_percentage(25, 100)
        25.0
        >>> calculate_percentage(1, 3, 2)
        33.33
    """
    
    percentage = safe_divide(value, total, 0) * 100
    return round(percentage, decimals)


def get_date_range(days: int = 90) -> tuple:
    """
    Get date range (start_date, end_date) untuk n hari terakhir.
    
    Args:
        days (int): Jumlah hari (default: 90)
        
    Returns:
        tuple: (start_date, end_date) sebagai datetime objects
        
    Example:
        >>> start, end = get_date_range(30)
    """
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return (start_date, end_date)


def is_critical_status(value, threshold) -> bool:
    """
    Determine apakah status critical berdasarkan value dan threshold.
    
    Args:
        value: Nilai actual
        threshold: Threshold value
        
    Returns:
        bool: True jika critical
        
    Example:
        >>> is_critical_status(5, 7)  # Days until stockout
        True
    """
    
    if pd.isna(value) or pd.isna(threshold):
        return False
    
    return float(value) < float(threshold)


def is_warning_status(value, low_threshold, high_threshold) -> bool:
    """
    Determine apakah status warning dalam range tertentu.
    
    Args:
        value: Nilai actual
        low_threshold: Lower threshold
        high_threshold: Upper threshold
        
    Returns:
        bool: True jika dalam warning range
        
    Example:
        >>> is_warning_status(10, 7, 14)  # Days until stockout
        True
    """
    
    if pd.isna(value) or pd.isna(low_threshold) or pd.isna(high_threshold):
        return False
    
    value = float(value)
    return float(low_threshold) <= value < float(high_threshold)


def get_risk_color(risk_level: str) -> str:
    """
    Get hex color based on risk level.
    
    Args:
        risk_level (str): 'Critical', 'High', 'Medium', 'Low'
        
    Returns:
        str: Hex color code
        
    Example:
        >>> get_risk_color('Critical')
        '#ef4444'
    """
    
    color_map = {
        'Critical': '#ef4444',
        'High': '#f59e0b',
        'Medium': '#3b82f6',
        'Low': '#10b981'
    }
    
    return color_map.get(risk_level, '#6366f1')


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text dan add ellipsis jika lebih panjang.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        
    Returns:
        str: Truncated text
        
    Example:
        >>> truncate_text('This is a very long product name', 20)
        'This is a very long...'
    """
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + '...'


def format_quantity(value, decimals: int = 0) -> str:
    """
    Format quantity dengan separators dan decimals.
    
    Args:
        value: Nilai quantity
        decimals (int): Decimal places
        
    Returns:
        str: Formatted quantity
        
    Example:
        >>> format_quantity(1500000, 0)
        '1,500,000'
    """
    
    if pd.isna(value):
        return '0'
    
    try:
        value = float(value)
        return f"{value:,.{decimals}f}"
    except:
        return str(value)


def days_until_date(target_date) -> int:
    """
    Calculate hari sampai target date.
    
    Args:
        target_date: Target date (datetime atau string 'YYYY-MM-DD')
        
    Returns:
        int: Days remaining (negative jika sudah lewat)
        
    Example:
        >>> days_until_date('2025-12-25')
    """
    
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d')
    
    today = datetime.now()
    delta = target_date - today
    
    return delta.days


def get_status_emoji(risk_level: str) -> str:
    """
    Get emoji untuk risk level.
    
    Args:
        risk_level (str): 'Critical', 'High', 'Medium', 'Low'
        
    Returns:
        str: Emoji representation
        
    Example:
        >>> get_status_emoji('Critical')
        '🔴'
    """
    
    emoji_map = {
        'Critical': '🔴',
        'High': '🟡',
        'Medium': '🔵',
        'Low': '🟢'
    }
    
    return emoji_map.get(risk_level, '⚪')
