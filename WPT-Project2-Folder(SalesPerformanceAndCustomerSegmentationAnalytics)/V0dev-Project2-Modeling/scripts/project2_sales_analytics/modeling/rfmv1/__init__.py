"""
RFM Modeling Package

This package provides advanced RFM analysis with:
- Customer Clustering (K-Means/DBSCAN)
- Churn Prediction (Classification)
- Customer Lifetime Value Prediction (Regression)

Author: Data Science Team
Version: 1.0.0
"""

from .config.rfm_config import RFMModelConfig
from .data.data_loader import RFMDataLoader

__version__ = "1.0.0"
__all__ = [
    "RFMModelConfig",
    "RFMDataLoader",
]
