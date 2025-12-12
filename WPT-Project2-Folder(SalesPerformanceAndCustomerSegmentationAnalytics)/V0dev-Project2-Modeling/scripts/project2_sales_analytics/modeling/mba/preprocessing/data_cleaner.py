"""
MBA Data Cleaner Module
=======================

Handles data cleaning and preparation before encoding.
Removes invalid transactions, handles missing values, and filters data.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Data cleaner for Market Basket Analysis preprocessing.
    
    Responsibilities:
    - Remove invalid/incomplete transactions
    - Handle missing values
    - Filter by minimum thresholds
    - Remove specified products
    
    Attributes:
        config: MBAConfig instance
        cleaning_stats: Statistics about cleaning operations
        
    Example:
        >>> cleaner = DataCleaner(config)
        >>> df_clean = cleaner.clean(df_raw)
        >>> cleaner.get_stats()
    """
    
    def __init__(self, config):
        """
        Initialize data cleaner.
        
        Args:
            config: MBAConfig instance with cleaning parameters
        """
        self.config = config
        self.cleaning_stats: Dict[str, int] = {}
        
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Execute full cleaning pipeline.
        
        Args:
            df: Raw transaction DataFrame
            
        Returns:
            Cleaned DataFrame ready for encoding
        """
        logger.info("Starting data cleaning pipeline...")
        
        original_rows = len(df)
        self.cleaning_stats['original_rows'] = original_rows
        
        # Step 1: Remove missing critical values
        df = self._remove_missing_values(df)
        
        # Step 2: Filter by minimum items per transaction
        df = self._filter_small_transactions(df)
        
        # Step 3: Filter infrequent products
        df = self._filter_infrequent_products(df)
        
        # Step 4: Remove excluded products
        df = self._remove_excluded_products(df)
        
        # Step 5: Filter by categories (if specified)
        df = self._filter_by_categories(df)
        
        # Step 6: Final cleanup
        df = self._final_cleanup(df)
        
        self.cleaning_stats['final_rows'] = len(df)
        self.cleaning_stats['rows_removed'] = original_rows - len(df)
        self.cleaning_stats['removal_pct'] = (original_rows - len(df)) / original_rows * 100
        
        logger.info(f"Cleaning complete: {len(df):,} rows remaining ({self.cleaning_stats['removal_pct']:.1f}% removed)")
        
        return df
    
    def _remove_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows with missing critical values."""
        critical_cols = [
            self.config.transaction_id_col,
            self.config.product_id_col
        ]
        
        before = len(df)
        
        for col in critical_cols:
            if col in df.columns:
                df = df.dropna(subset=[col])
        
        self.cleaning_stats['missing_removed'] = before - len(df)
        
        if self.config.verbose and before - len(df) > 0:
            logger.info(f"   Removed {before - len(df):,} rows with missing values")
        
        return df
    
    def _filter_small_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove transactions with fewer items than threshold.
        
        Single-item transactions don't contribute to association rules.
        """
        before = len(df)
        
        # Count items per transaction
        items_per_txn = df.groupby(self.config.transaction_id_col)[self.config.product_id_col].nunique()
        
        # Get transactions meeting threshold
        valid_txns = items_per_txn[items_per_txn >= self.config.min_items_per_transaction].index
        
        # Filter DataFrame
        df = df[df[self.config.transaction_id_col].isin(valid_txns)]
        
        self.cleaning_stats['small_txn_removed'] = before - len(df)
        self.cleaning_stats['transactions_filtered'] = len(items_per_txn) - len(valid_txns)
        
        if self.config.verbose:
            logger.info(f"   Removed {len(items_per_txn) - len(valid_txns):,} transactions with < {self.config.min_items_per_transaction} items")
        
        return df
    
    def _filter_infrequent_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove products that appear in very few transactions."""
        before = len(df)
        
        # Count transactions per product
        product_counts = df.groupby(self.config.product_id_col)[self.config.transaction_id_col].nunique()
        
        # Get products meeting threshold
        valid_products = product_counts[product_counts >= self.config.min_transactions_per_product].index
        
        # Filter DataFrame
        df = df[df[self.config.product_id_col].isin(valid_products)]
        
        self.cleaning_stats['infrequent_products_removed'] = len(product_counts) - len(valid_products)
        
        if self.config.verbose:
            logger.info(f"   Removed {len(product_counts) - len(valid_products):,} infrequent products (< {self.config.min_transactions_per_product} transactions)")
        
        return df
    
    def _remove_excluded_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove specifically excluded products."""
        if not self.config.exclude_products:
            return df
        
        before = len(df)
        
        # Handle both product ID and name columns
        product_col = self.config.product_id_col
        
        df = df[~df[product_col].isin(self.config.exclude_products)]
        
        # Also check product name if available
        if self.config.product_name_col in df.columns:
            df = df[~df[self.config.product_name_col].isin(self.config.exclude_products)]
        
        self.cleaning_stats['excluded_removed'] = before - len(df)
        
        if self.config.verbose and before - len(df) > 0:
            logger.info(f"   Removed {before - len(df):,} rows for excluded products")
        
        return df
    
    def _filter_by_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to include only specified categories."""
        if not self.config.include_categories:
            return df
        
        # Check for category column (common names)
        category_cols = ['category', 'product_category', 'item_category', 'category_id']
        
        category_col = None
        for col in category_cols:
            if col in df.columns:
                category_col = col
                break
        
        if not category_col:
            logger.warning("Category column not found, skipping category filter")
            return df
        
        before = len(df)
        df = df[df[category_col].isin(self.config.include_categories)]
        
        self.cleaning_stats['category_filtered'] = before - len(df)
        
        if self.config.verbose:
            logger.info(f"   Filtered to categories: {self.config.include_categories}")
        
        return df
    
    def _final_cleanup(self, df: pd.DataFrame) -> pd.DataFrame:
        """Final cleanup operations."""
        # Reset index
        df = df.reset_index(drop=True)
        
        # Ensure proper dtypes
        if self.config.transaction_id_col in df.columns:
            df[self.config.transaction_id_col] = df[self.config.transaction_id_col].astype(str)
        
        if self.config.product_id_col in df.columns:
            df[self.config.product_id_col] = df[self.config.product_id_col].astype(str)
        
        return df
    
    def get_stats(self) -> Dict[str, int]:
        """Return cleaning statistics."""
        return self.cleaning_stats
    
    def print_stats(self) -> None:
        """Print cleaning statistics summary."""
        print("\n" + "=" * 60)
        print("DATA CLEANING SUMMARY")
        print("=" * 60)
        
        print(f"Original rows:        {self.cleaning_stats.get('original_rows', 0):,}")
        print(f"Missing removed:      {self.cleaning_stats.get('missing_removed', 0):,}")
        print(f"Small txn removed:    {self.cleaning_stats.get('small_txn_removed', 0):,}")
        print(f"Infrequent products:  {self.cleaning_stats.get('infrequent_products_removed', 0):,}")
        print(f"Excluded removed:     {self.cleaning_stats.get('excluded_removed', 0):,}")
        print("-" * 60)
        print(f"Final rows:           {self.cleaning_stats.get('final_rows', 0):,}")
        print(f"Removal percentage:   {self.cleaning_stats.get('removal_pct', 0):.1f}%")
