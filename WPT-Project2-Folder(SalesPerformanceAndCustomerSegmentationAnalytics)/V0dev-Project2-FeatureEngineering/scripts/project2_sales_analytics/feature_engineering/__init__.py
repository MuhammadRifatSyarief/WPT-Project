"""
Feature Engineering Module for Sales Performance Analytics

This module provides modular feature extraction capabilities for:
- Customer segmentation (RFM-based)
- Product performance analysis
- Transaction pattern analysis
- Market basket analysis

Author: v0
Version: 1.0
"""

from .pipeline.feature_pipeline import FeatureEngineeringPipeline
from .config.feature_config import FeatureConfig

__version__ = "1.0.0"
__all__ = [
    "FeatureEngineeringPipeline",
    "FeatureConfig",
]
