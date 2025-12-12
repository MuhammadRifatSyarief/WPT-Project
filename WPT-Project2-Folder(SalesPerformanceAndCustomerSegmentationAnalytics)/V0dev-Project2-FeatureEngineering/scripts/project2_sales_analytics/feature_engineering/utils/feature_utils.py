"""
Feature Engineering Utility Functions

Helper functions yang digunakan across semua feature extractors.

Author: v0
Version: 1.0
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple, Union, Dict, Any
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_divide(
    numerator: Union[pd.Series, np.ndarray, float],
    denominator: Union[pd.Series, np.ndarray, float],
    fill_value: float = 0.0
) -> Union[pd.Series, np.ndarray, float]:
    """
    Safe division that handles division by zero.
    
    Parameters
    ----------
    numerator : numeric
        The numerator value(s)
    denominator : numeric
        The denominator value(s)
    fill_value : float
        Value to use when division by zero occurs
        
    Returns
    -------
    numeric
        Result of division with fill_value where denominator is 0
        
    Example
    -------
    >>> safe_divide(10, 0)
    0.0
    >>> safe_divide(pd.Series([10, 20]), pd.Series([2, 0]))
    0    5.0
    1    0.0
    dtype: float64
    """
    if isinstance(numerator, pd.Series) or isinstance(denominator, pd.Series):
        result = numerator / denominator
        if isinstance(result, pd.Series):
            result = result.replace([np.inf, -np.inf], fill_value)
            result = result.fillna(fill_value)
        return result
    else:
        if denominator == 0:
            return fill_value
        return numerator / denominator


def calculate_percentile_rank(
    series: pd.Series,
    method: str = "average"
) -> pd.Series:
    """
    Calculate percentile rank (0-100) for each value in series.
    
    Parameters
    ----------
    series : pd.Series
        Input series to rank
    method : str
        Ranking method: 'average', 'min', 'max', 'first', 'dense'
        
    Returns
    -------
    pd.Series
        Percentile ranks (0-100)
        
    Example
    -------
    >>> s = pd.Series([10, 20, 30, 40, 50])
    >>> calculate_percentile_rank(s)
    0    10.0
    1    30.0
    2    50.0
    3    70.0
    4    90.0
    dtype: float64
    """
    return series.rank(method=method, pct=True) * 100


def detect_outliers(
    series: pd.Series,
    method: str = "iqr",
    threshold: float = 1.5
) -> pd.Series:
    """
    Detect outliers in a series.
    
    Parameters
    ----------
    series : pd.Series
        Input series
    method : str
        Detection method: 'iqr' (Interquartile Range) or 'zscore'
    threshold : float
        IQR multiplier (default 1.5) or z-score threshold (default 3)
        
    Returns
    -------
    pd.Series
        Boolean series indicating outliers (True = outlier)
        
    Example
    -------
    >>> s = pd.Series([1, 2, 3, 4, 100])
    >>> detect_outliers(s, method='iqr')
    0    False
    1    False
    2    False
    3    False
    4     True
    dtype: bool
    """
    if method == "iqr":
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        return (series < lower_bound) | (series > upper_bound)
    
    elif method == "zscore":
        mean = series.mean()
        std = series.std()
        if std == 0:
            return pd.Series([False] * len(series), index=series.index)
        z_scores = (series - mean) / std
        return z_scores.abs() > threshold
    
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr' or 'zscore'")


def normalize_series(
    series: pd.Series,
    method: str = "minmax"
) -> pd.Series:
    """
    Normalize a series using specified method.
    
    Parameters
    ----------
    series : pd.Series
        Input series to normalize
    method : str
        Normalization method: 'minmax', 'zscore', 'robust'
        
    Returns
    -------
    pd.Series
        Normalized series
        
    Example
    -------
    >>> s = pd.Series([10, 20, 30, 40, 50])
    >>> normalize_series(s, method='minmax')
    0    0.00
    1    0.25
    2    0.50
    3    0.75
    4    1.00
    dtype: float64
    """
    if method == "minmax":
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series([0.5] * len(series), index=series.index)
        return (series - min_val) / (max_val - min_val)
    
    elif method == "zscore":
        mean = series.mean()
        std = series.std()
        if std == 0:
            return pd.Series([0.0] * len(series), index=series.index)
        return (series - mean) / std
    
    elif method == "robust":
        median = series.median()
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        if IQR == 0:
            return pd.Series([0.0] * len(series), index=series.index)
        return (series - median) / IQR
    
    else:
        raise ValueError(f"Unknown method: {method}")


def encode_categorical(
    series: pd.Series,
    method: str = "label",
    categories: Optional[List] = None
) -> Union[pd.Series, pd.DataFrame]:
    """
    Encode categorical variables.
    
    Parameters
    ----------
    series : pd.Series
        Categorical series to encode
    method : str
        Encoding method: 'label', 'onehot', 'frequency'
    categories : list, optional
        Explicit category order for label encoding
        
    Returns
    -------
    pd.Series or pd.DataFrame
        Encoded values (Series for label/frequency, DataFrame for onehot)
        
    Example
    -------
    >>> s = pd.Series(['A', 'B', 'A', 'C'])
    >>> encode_categorical(s, method='label')
    0    0
    1    1
    2    0
    3    2
    dtype: int64
    """
    if method == "label":
        if categories:
            cat_type = pd.CategoricalDtype(categories=categories, ordered=True)
            return series.astype(cat_type).cat.codes
        return series.astype("category").cat.codes
    
    elif method == "onehot":
        return pd.get_dummies(series, prefix=series.name)
    
    elif method == "frequency":
        freq = series.value_counts(normalize=True)
        return series.map(freq)
    
    else:
        raise ValueError(f"Unknown method: {method}")


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: List[str],
    numeric_columns: Optional[List[str]] = None,
    non_null_columns: Optional[List[str]] = None,
    raise_error: bool = True
) -> Tuple[bool, List[str]]:
    """
    Validate DataFrame for required structure and data quality.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to validate
    required_columns : list
        Columns that must exist
    numeric_columns : list, optional
        Columns that must be numeric
    non_null_columns : list, optional
        Columns that cannot have null values
    raise_error : bool
        Whether to raise error on validation failure
        
    Returns
    -------
    tuple
        (is_valid: bool, errors: list of error messages)
        
    Example
    -------
    >>> df = pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']})
    >>> validate_dataframe(df, required_columns=['a', 'b', 'c'])
    (False, ['Missing required columns: c'])
    """
    errors = []
    
    # Check required columns
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
    
    # Check numeric columns
    if numeric_columns:
        for col in numeric_columns:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Column '{col}' must be numeric")
    
    # Check non-null columns
    if non_null_columns:
        for col in non_null_columns:
            if col in df.columns and df[col].isnull().any():
                null_count = df[col].isnull().sum()
                errors.append(f"Column '{col}' has {null_count} null values")
    
    is_valid = len(errors) == 0
    
    if not is_valid and raise_error:
        raise ValueError(f"DataFrame validation failed:\n" + "\n".join(errors))
    
    return is_valid, errors


def log_progress(
    message: str,
    level: str = "info",
    prefix: str = "   "
) -> None:
    """
    Log progress message with consistent formatting.
    
    Parameters
    ----------
    message : str
        Message to log
    level : str
        Log level: 'info', 'warning', 'error', 'debug'
    prefix : str
        Prefix for the message
        
    Example
    -------
    >>> log_progress("Processing 100 records", level="info")
       [INFO] Processing 100 records
    """
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"{prefix}{message}")


def calculate_recency(
    last_purchase_date: pd.Series,
    reference_date: Optional[datetime] = None
) -> pd.Series:
    """
    Calculate recency (days since last purchase).
    
    Parameters
    ----------
    last_purchase_date : pd.Series
        Series of last purchase dates
    reference_date : datetime, optional
        Reference date for calculation (default: today)
        
    Returns
    -------
    pd.Series
        Days since last purchase
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    # Ensure datetime type
    last_purchase_date = pd.to_datetime(last_purchase_date)
    
    # Calculate days difference
    recency = (reference_date - last_purchase_date).dt.days
    
    return recency


def bin_values(
    series: pd.Series,
    bins: Union[int, List[float]],
    labels: Optional[List[str]] = None
) -> pd.Series:
    """
    Bin continuous values into categories.
    
    Parameters
    ----------
    series : pd.Series
        Continuous series to bin
    bins : int or list
        Number of bins or bin edges
    labels : list, optional
        Labels for the bins
        
    Returns
    -------
    pd.Series
        Binned categories
    """
    return pd.cut(series, bins=bins, labels=labels, include_lowest=True)


def calculate_coefficient_of_variation(series: pd.Series) -> float:
    """
    Calculate coefficient of variation (CV = std/mean).
    
    Parameters
    ----------
    series : pd.Series
        Input series
        
    Returns
    -------
    float
        Coefficient of variation (0 if mean is 0)
    """
    mean = series.mean()
    std = series.std()
    
    if mean == 0:
        return 0.0
    
    return std / mean


def create_feature_summary(
    features_df: pd.DataFrame,
    feature_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Create summary statistics for features.
    
    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing features
    feature_columns : list, optional
        Specific columns to summarize (default: all numeric)
        
    Returns
    -------
    pd.DataFrame
        Summary statistics
    """
    if feature_columns is None:
        feature_columns = features_df.select_dtypes(include=[np.number]).columns.tolist()
    
    summary = features_df[feature_columns].describe()
    summary.loc['missing'] = features_df[feature_columns].isnull().sum()
    summary.loc['missing_pct'] = (features_df[feature_columns].isnull().sum() / len(features_df) * 100).round(2)
    
    return summary
