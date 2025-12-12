"""Utility functions for feature engineering."""

import sys
from pathlib import Path

_PARENT_DIR = Path(__file__).resolve().parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from utils.feature_utils import (
    safe_divide,
    calculate_percentile_rank,
    detect_outliers,
    normalize_series,
    encode_categorical,
    validate_dataframe,
    log_progress,
    calculate_coefficient_of_variation,
    calculate_recency,
    bin_values,
    create_feature_summary,
)

__all__ = [
    "safe_divide",
    "calculate_percentile_rank", 
    "detect_outliers",
    "normalize_series",
    "encode_categorical",
    "validate_dataframe",
    "log_progress",
    "calculate_coefficient_of_variation",
    "calculate_recency",
    "bin_values",
    "create_feature_summary",
]
