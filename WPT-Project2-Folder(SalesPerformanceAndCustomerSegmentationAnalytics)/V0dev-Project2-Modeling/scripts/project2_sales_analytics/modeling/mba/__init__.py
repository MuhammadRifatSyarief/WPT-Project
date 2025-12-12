"""
Market Basket Analysis (MBA) Module
===================================

This module provides functionality for:
- Transaction data preprocessing
- Apriori/FP-Growth algorithm implementation
- Association rules generation and analysis
- Cross-sell recommendations

Usage:
    from mba import run_mba_pipeline
    results = run_mba_pipeline(config_path='config/mba_config.py')
"""

__version__ = "1.0.0"
__author__ = "Project 2 - Sales Analytics"

from .config.mba_config import MBAConfig
from .data.data_loader import MBADataLoader
from .preprocessing.transaction_encoder import TransactionEncoder
from .algorithms.apriori_runner import AprioriRunner
from .algorithms.fpgrowth_runner import FPGrowthRunner
from .analysis.rules_analyzer import RulesAnalyzer
from .export.mba_exporter import MBAExporter

__all__ = [
    'MBAConfig',
    'MBADataLoader', 
    'TransactionEncoder',
    'AprioriRunner',
    'FPGrowthRunner',
    'RulesAnalyzer',
    'MBAExporter'
]
