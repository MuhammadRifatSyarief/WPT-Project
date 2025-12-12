"""
MBA Data Loader Module
======================

Handles loading transaction data from various sources (CSV, PKL, Excel)
and provides data validation and preview functionality.

Author: Project 2 - Sales Analytics
Version: 1.1.0
"""

import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MBADataLoader:
    """
    Data loader for Market Basket Analysis.
    
    Supports loading from:
    - CSV files
    - Pickle files (from feature engineering)
    - Excel files
    
    Loads data from feature engineering output:
    - sales_details.csv (primary transaction data)
    - sales_by_product.csv (product enrichment)
    - rfm_features.csv (customer segment filtering)
    - behavioral_features.csv (customer behavior)
    
    Attributes:
        config: MBAConfig instance
        df: Loaded DataFrame
        metadata: Data metadata
        
    Example:
        >>> loader = MBADataLoader(config)
        >>> df = loader.load()
        >>> loader.preview()
    """
    
    def __init__(self, config):
        """
        Initialize data loader.
        
        Args:
            config: MBAConfig instance with data paths and column mappings
        """
        self.config = config
        self.df: Optional[pd.DataFrame] = None
        self.product_df: Optional[pd.DataFrame] = None
        self.rfm_df: Optional[pd.DataFrame] = None
        self.behavioral_df: Optional[pd.DataFrame] = None
        self.metadata: Dict[str, Any] = {}
        
    def load(self, path: Optional[str] = None) -> pd.DataFrame:
        """
        Load transaction data from file.
        
        Args:
            path: Optional override for input path
            
        Returns:
            DataFrame with transaction data
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file format is not supported
        """
        input_path = Path(path or self.config.input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        logger.info(f"Loading data from: {input_path}")
        
        # Load based on file extension
        suffix = input_path.suffix.lower()
        
        if suffix == '.csv':
            self.df = self._load_csv(input_path)
        elif suffix == '.pkl':
            self.df = self._load_pickle(input_path)
        elif suffix in ['.xlsx', '.xls']:
            self.df = self._load_excel(input_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        # Store metadata
        self._generate_metadata()
        
        logger.info(f"Loaded {len(self.df):,} rows, {len(self.df.columns)} columns")
        
        return self.df
    
    def load_all_feature_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load all feature engineering output files.
        
        Returns:
            Dictionary with all loaded DataFrames
        """
        data = {}
        
        # Load sales_details (primary)
        self.df = self.load(self.config.sales_details_path)
        data['sales_details'] = self.df
        
        # Load product data for enrichment
        if Path(self.config.sales_by_product_path).exists():
            self.product_df = pd.read_csv(self.config.sales_by_product_path)
            data['sales_by_product'] = self.product_df
            logger.info(f"Loaded product data: {len(self.product_df):,} products")
        
        # Load RFM data for segment filtering
        if Path(self.config.rfm_features_path).exists():
            self.rfm_df = pd.read_csv(self.config.rfm_features_path)
            data['rfm_features'] = self.rfm_df
            logger.info(f"Loaded RFM data: {len(self.rfm_df):,} customers")
        
        # Load behavioral features
        if Path(self.config.behavioral_features_path).exists():
            self.behavioral_df = pd.read_csv(self.config.behavioral_features_path)
            data['behavioral_features'] = self.behavioral_df
            logger.info(f"Loaded behavioral data: {len(self.behavioral_df):,} customers")
        
        return data
    
    def filter_by_rfm_segment(
        self, 
        segments: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Filter transactions by customer RFM segment.
        
        Args:
            segments: List of RFM segments to include
                     e.g., ['Champions', 'Loyal', 'Potential Loyalists']
        
        Returns:
            Filtered DataFrame
        """
        if self.df is None:
            raise ValueError("No data loaded. Call load() first.")
        
        if self.rfm_df is None:
            logger.warning("RFM data not loaded. Loading now...")
            if Path(self.config.rfm_features_path).exists():
                self.rfm_df = pd.read_csv(self.config.rfm_features_path)
            else:
                logger.warning("RFM file not found. Returning unfiltered data.")
                return self.df
        
        segments = segments or self.config.target_rfm_segments
        
        if not segments:
            return self.df
        
        # Get customers in target segments
        segment_customers = self.rfm_df[
            self.rfm_df[self.config.rfm_segment_col].isin(segments)
        ][self.config.customer_id_col].unique()
        
        # Filter transactions
        filtered_df = self.df[
            self.df[self.config.customer_id_col].isin(segment_customers)
        ].copy()
        
        logger.info(f"Filtered to {len(filtered_df):,} transactions from {len(segment_customers):,} customers in segments: {segments}")
        
        return filtered_df
    
    def filter_by_value_tier(
        self, 
        tiers: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Filter transactions by customer value tier.
        
        Args:
            tiers: List of value tiers to include
                   e.g., ['High', 'Medium']
        
        Returns:
            Filtered DataFrame
        """
        if self.df is None:
            raise ValueError("No data loaded. Call load() first.")
        
        if self.rfm_df is None:
            if Path(self.config.rfm_features_path).exists():
                self.rfm_df = pd.read_csv(self.config.rfm_features_path)
            else:
                return self.df
        
        tiers = tiers or self.config.target_value_tiers
        
        if not tiers:
            return self.df
        
        # Get customers in target tiers
        tier_customers = self.rfm_df[
            self.rfm_df[self.config.value_tier_col].isin(tiers)
        ][self.config.customer_id_col].unique()
        
        # Filter transactions
        filtered_df = self.df[
            self.df[self.config.customer_id_col].isin(tier_customers)
        ].copy()
        
        logger.info(f"Filtered to {len(filtered_df):,} transactions from {len(tier_customers):,} customers in tiers: {tiers}")
        
        return filtered_df
    
    def enrich_with_product_data(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Enrich transaction data with product metrics from sales_by_product.csv.
        
        Adds columns:
        - total_quantity_sold
        - total_revenue
        - order_count
        - unique_customers
        - revenue_contribution_pct
        
        Args:
            df: DataFrame to enrich (default: self.df)
            
        Returns:
            Enriched DataFrame
        """
        df = df if df is not None else self.df
        
        if df is None:
            raise ValueError("No data to enrich. Load data first.")
        
        if self.product_df is None:
            if Path(self.config.sales_by_product_path).exists():
                self.product_df = pd.read_csv(self.config.sales_by_product_path)
            else:
                logger.warning("Product data not found. Returning original data.")
                return df
        
        # Select columns to merge
        product_cols = [
            self.config.product_id_col,
            self.config.total_quantity_sold_col,
            self.config.total_revenue_col,
            self.config.order_count_col,
            self.config.unique_customers_col,
            self.config.revenue_contribution_col
        ]
        
        # Only include columns that exist
        product_cols = [c for c in product_cols if c in self.product_df.columns]
        
        if len(product_cols) > 1:  # At least product_id + 1 metric
            enriched_df = df.merge(
                self.product_df[product_cols],
                on=self.config.product_id_col,
                how='left'
            )
            logger.info(f"Enriched with {len(product_cols)-1} product metrics")
            return enriched_df
        
        return df
    
    def _load_csv(self, path: Path) -> pd.DataFrame:
        """Load CSV file with proper parsing."""
        df = pd.read_csv(
            path,
            parse_dates=[self.config.date_col] if self.config.date_col else None,
            low_memory=False
        )
        return df
    
    def _load_pickle(self, path: Path) -> pd.DataFrame:
        """Load pickle file (from feature engineering output)."""
        data = joblib.load(path)
        
        # Handle streamlit_data.pkl format
        if isinstance(data, dict) and 'data' in data:
            if 'sales_details' in data['data']:
                return data['data']['sales_details']
            else:
                # Return first available DataFrame
                for key, value in data['data'].items():
                    if isinstance(value, pd.DataFrame):
                        logger.info(f"Using '{key}' from pickle")
                        return value
                        
        # Direct DataFrame
        if isinstance(data, pd.DataFrame):
            return data
            
        raise ValueError("Could not extract DataFrame from pickle file")
    
    def _load_excel(self, path: Path, sheet_name: str = "5_Sales_Details") -> pd.DataFrame:
        """Load Excel file."""
        df = pd.read_excel(path, sheet_name=sheet_name)
        return df
    
    def _generate_metadata(self) -> None:
        """Generate metadata about loaded data."""
        self.metadata = {
            'rows': len(self.df),
            'columns': len(self.df.columns),
            'column_names': list(self.df.columns),
            'memory_mb': self.df.memory_usage(deep=True).sum() / 1024 / 1024,
            'null_counts': self.df.isnull().sum().to_dict(),
            'dtypes': self.df.dtypes.astype(str).to_dict()
        }
        
        # Transaction-specific metadata
        if self.config.transaction_id_col in self.df.columns:
            self.metadata['unique_transactions'] = self.df[self.config.transaction_id_col].nunique()
            
        if self.config.product_id_col in self.df.columns:
            self.metadata['unique_products'] = self.df[self.config.product_id_col].nunique()
            
        if self.config.customer_id_col in self.df.columns:
            self.metadata['unique_customers'] = self.df[self.config.customer_id_col].nunique()
            
        if self.config.product_category_col in self.df.columns:
            self.metadata['unique_categories'] = self.df[self.config.product_category_col].nunique()
            self.metadata['categories'] = self.df[self.config.product_category_col].unique().tolist()
    
    def validate(self) -> Tuple[bool, list]:
        """
        Validate loaded data for MBA requirements.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        warnings = []
        
        if self.df is None:
            return False, ["No data loaded. Call load() first."]
        
        # Check required columns
        required_cols = [
            self.config.transaction_id_col,
            self.config.product_id_col
        ]
        
        for col in required_cols:
            if col not in self.df.columns:
                errors.append(f"Required column missing: {col}")
        
        # Check recommended columns from feature engineering
        recommended_cols = [
            self.config.product_name_col,
            self.config.customer_id_col,
            self.config.product_category_col,
            self.config.quantity_col,
            self.config.amount_col
        ]
        
        for col in recommended_cols:
            if col not in self.df.columns:
                warnings.append(f"Recommended column missing: {col}")
        
        # Check for sufficient transactions
        if self.config.transaction_id_col in self.df.columns:
            n_transactions = self.df[self.config.transaction_id_col].nunique()
            if n_transactions < 100:
                warnings.append(f"Low transaction count ({n_transactions}). Results may be unreliable.")
        
        # Check for sufficient products
        if self.config.product_id_col in self.df.columns:
            n_products = self.df[self.config.product_id_col].nunique()
            if n_products < 10:
                warnings.append(f"Low product count ({n_products}). Limited association patterns expected.")
        
        is_valid = len(errors) == 0
        
        if self.config.verbose:
            self._print_validation_results(errors, warnings)
        
        return is_valid, errors + warnings
    
    def _print_validation_results(self, errors: list, warnings: list) -> None:
        """Print validation results."""
        print("\n" + "=" * 60)
        print("DATA VALIDATION")
        print("=" * 60)
        
        if errors:
            for error in errors:
                print(f"[ERROR] {error}")
        
        if warnings:
            for warning in warnings:
                print(f"[WARN] {warning}")
        
        if not errors and not warnings:
            print("[OK] All validations passed")
        
        print("-" * 60)
    
    def preview(self, n: int = 5) -> None:
        """
        Print data preview and statistics.
        
        Args:
            n: Number of rows to display
        """
        if self.df is None:
            print("No data loaded. Call load() first.")
            return
        
        print("\n" + "=" * 60)
        print("DATA PREVIEW - Feature Engineering Output")
        print("=" * 60)
        
        print(f"\nShape: {self.df.shape[0]:,} rows x {self.df.shape[1]} columns")
        print(f"Memory: {self.metadata.get('memory_mb', 0):.2f} MB")
        
        print(f"\n--- First {n} rows ---")
        print(self.df.head(n).to_string())
        
        print(f"\n--- Column Types ---")
        print(self.df.dtypes.to_string())
        
        if self.metadata:
            print(f"\n--- Transaction Summary ---")
            print(f"Unique Transactions: {self.metadata.get('unique_transactions', 'N/A'):,}")
            print(f"Unique Products: {self.metadata.get('unique_products', 'N/A'):,}")
            print(f"Unique Customers: {self.metadata.get('unique_customers', 'N/A'):,}")
            print(f"Unique Categories: {self.metadata.get('unique_categories', 'N/A')}")
    
    def get_transaction_stats(self) -> pd.DataFrame:
        """
        Calculate transaction-level statistics.
        
        Returns:
            DataFrame with transaction statistics
        """
        if self.df is None:
            raise ValueError("No data loaded. Call load() first.")
        
        stats = self.df.groupby(self.config.transaction_id_col).agg({
            self.config.product_id_col: 'nunique',
            self.config.quantity_col: 'sum' if self.config.quantity_col in self.df.columns else 'count',
            self.config.amount_col: 'sum' if self.config.amount_col in self.df.columns else 'count'
        }).reset_index()
        
        stats.columns = ['transaction_id', 'unique_products', 'total_quantity', 'total_amount']
        
        return stats
    
    def get_product_stats(self) -> pd.DataFrame:
        """
        Calculate product-level statistics.
        
        Returns:
            DataFrame with product statistics
        """
        if self.df is None:
            raise ValueError("No data loaded. Call load() first.")
        
        stats = self.df.groupby(self.config.product_id_col).agg({
            self.config.transaction_id_col: 'nunique',
            self.config.quantity_col: 'sum' if self.config.quantity_col in self.df.columns else 'count',
            self.config.amount_col: 'sum' if self.config.amount_col in self.df.columns else 'count'
        }).reset_index()
        
        stats.columns = ['product_id', 'transaction_count', 'total_quantity', 'total_revenue']
        stats = stats.sort_values('transaction_count', ascending=False)
        
        return stats
    
    def get_segment_distribution(self) -> pd.DataFrame:
        """
        Get customer segment distribution from RFM data.
        
        Returns:
            DataFrame with segment counts
        """
        if self.rfm_df is None:
            if Path(self.config.rfm_features_path).exists():
                self.rfm_df = pd.read_csv(self.config.rfm_features_path)
            else:
                return pd.DataFrame()
        
        dist = self.rfm_df[self.config.rfm_segment_col].value_counts().reset_index()
        dist.columns = ['segment', 'customer_count']
        dist['percentage'] = dist['customer_count'] / dist['customer_count'].sum() * 100
        
        return dist
