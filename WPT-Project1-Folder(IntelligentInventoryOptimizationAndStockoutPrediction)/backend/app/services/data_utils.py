"""
Data Utilities
==============
Helper functions common for data processing.
"""

import pandas as pd
import numpy as np
import json

def df_to_json(df: pd.DataFrame, orient='records'):
    """
    Konversi DataFrame ke JSON-serializable structure.
    Menghandle NaN, timestamp, dan tipe data lain yang tricky.
    """
    if df is None or df.empty:
        return []
        
    # Copy untuk menghindari modifikasi source
    dff = df.copy()
    
    # Handle datetime
    for col in dff.select_dtypes(include=['datetime64', 'datetimetz']).columns:
        dff[col] = dff[col].astype(str)
        
    # Handle NaN/Inf -> None (valid JSON null)
    dff = dff.replace({np.nan: None, np.inf: None, -np.inf: None})
    
    return dff.to_dict(orient=orient)

def safe_float(value, default=0.0):
    """Konversi aman ke float."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def paginate_df(df: pd.DataFrame, page: int = 1, per_page: int = 50):
    """Simple pagination utility for DataFrame."""
    total = len(df)
    start = (page - 1) * per_page
    end = start + per_page
    
    items = df_to_json(df.iloc[start:end])
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }
