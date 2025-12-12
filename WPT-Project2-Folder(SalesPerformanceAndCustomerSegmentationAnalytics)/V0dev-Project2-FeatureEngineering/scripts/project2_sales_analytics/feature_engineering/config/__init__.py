"""Configuration module for feature engineering."""

import sys
from pathlib import Path

_PARENT_DIR = Path(__file__).resolve().parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from config.feature_config import (
    FeatureConfig,
    RFMConfig,
    BehavioralConfig,
    TemporalConfig,
    ProductConfig,
    BasketConfig,
    TransactionConfig,
    DEFAULT_CONFIG,
)

__all__ = [
    "FeatureConfig",
    "RFMConfig",
    "BehavioralConfig",
    "TemporalConfig",
    "ProductConfig",
    "BasketConfig",
    "TransactionConfig",
    "DEFAULT_CONFIG",
]
