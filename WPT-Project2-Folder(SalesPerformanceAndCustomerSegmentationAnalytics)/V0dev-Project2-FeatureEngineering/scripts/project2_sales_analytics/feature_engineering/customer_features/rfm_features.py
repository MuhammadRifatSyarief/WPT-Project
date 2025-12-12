"""
RFM Feature Extractor

Extract and enhance RFM (Recency, Frequency, Monetary) features
untuk customer segmentation.

Author: v0
Version: 1.1 - Updated with flexible column detection
"""

import sys
from pathlib import Path

_PARENT_DIR = Path(__file__).resolve().parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config.feature_config import FeatureConfig, RFMConfig
from utils.feature_utils import (
    safe_divide,
    calculate_percentile_rank,
    validate_dataframe,
    log_progress,
)


class RFMFeatureExtractor:
    """
    Extract RFM-based features from customer transaction data.
    
    Features extracted:
    - Basic RFM: recency, frequency, monetary
    - RFM Scores: r_score, f_score, m_score (1-5)
    - Combined: rfm_score, rfm_segment
    - Enhanced: avg_order_value, purchase_rate, monetary_rank
    
    Example
    -------
    >>> extractor = RFMFeatureExtractor()
    >>> features = extractor.extract(sales_details_df, reference_date="2024-12-31")
    >>> print(features.columns)
    """
    
    def __init__(self, config: Optional[RFMConfig] = None):
        """
        Initialize RFM Feature Extractor.
        
        Parameters
        ----------
        config : RFMConfig, optional
            Configuration object. If None, uses default config.
        """
        self.config = config or RFMConfig()
        self._reference_date: Optional[datetime] = None
        
    def extract(
        self,
        sales_details: pd.DataFrame,
        reference_date: Optional[str] = None,
        customer_id_col: str = "customer_id",
        date_col: str = "transaction_date",
        amount_col: str = "total_amount",
    ) -> pd.DataFrame:
        """
        Extract RFM features from transaction-level data.
        
        Parameters
        ----------
        sales_details : pd.DataFrame
            Transaction-level sales data
        reference_date : str, optional
            Reference date for recency calculation (YYYY-MM-DD)
        customer_id_col : str
            Column name for customer ID
        date_col : str
            Column name for transaction date
        amount_col : str
            Column name for transaction amount
            
        Returns
        -------
        pd.DataFrame
            Customer data with RFM features added
        """
        log_progress("Starting RFM feature extraction...")
        
        # Set reference date
        if reference_date:
            self._reference_date = pd.to_datetime(reference_date)
        else:
            self._reference_date = pd.to_datetime(datetime.now().date())
        
        df = sales_details.copy()
        
        try:
            df[date_col] = pd.to_datetime(df[date_col])
        except Exception as e:
            log_progress(f"Warning: Could not convert {date_col} to datetime: {e}")
            # Try to find any date-like column
            date_cols = [c for c in df.columns if "date" in c.lower()]
            if date_cols:
                date_col = date_cols[0]
                df[date_col] = pd.to_datetime(df[date_col])
                log_progress(f"Using fallback date column: {date_col}")
            else:
                raise ValueError(f"No valid date column found. Tried: {date_col}")
        
        # Step 1: Aggregate to customer level
        rfm_data = self._aggregate_customer_data(
            df, customer_id_col, date_col, amount_col
        )
        
        # Step 2: Calculate RFM scores (1-5)
        rfm_data = self._calculate_rfm_scores(rfm_data)
        
        # Step 3: Calculate combined RFM score
        rfm_data = self._calculate_combined_score(rfm_data)
        
        # Step 4: Assign segments
        rfm_data = self._assign_segments(rfm_data)
        
        # Step 5: Calculate enhanced metrics
        rfm_data = self._calculate_enhanced_metrics(rfm_data)
        
        log_progress(f"RFM features extracted for {len(rfm_data)} customers")
        
        return rfm_data
    
    def _aggregate_customer_data(
        self,
        df: pd.DataFrame,
        customer_id_col: str,
        date_col: str,
        amount_col: str,
    ) -> pd.DataFrame:
        """Aggregate transaction data to customer level."""
        log_progress("Aggregating customer data...")
        
        rfm_agg = df.groupby(customer_id_col).agg({
            date_col: "max",  # Last purchase date
            amount_col: ["sum", "count", "mean"]  # Monetary metrics
        }).reset_index()
        
        # Flatten column names
        rfm_agg.columns = [
            customer_id_col, "last_purchase_date", 
            "monetary", "frequency", "avg_transaction_value"
        ]
        
        # Calculate recency
        rfm_agg["recency"] = (
            self._reference_date - pd.to_datetime(rfm_agg["last_purchase_date"])
        ).dt.days
        
        # Handle edge cases
        rfm_agg["recency"] = rfm_agg["recency"].fillna(rfm_agg["recency"].max()).astype(int)
        rfm_agg["frequency"] = rfm_agg["frequency"].fillna(0).astype(int)
        rfm_agg["monetary"] = rfm_agg["monetary"].fillna(0)
        
        return rfm_agg
    
    def _calculate_rfm_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RFM scores using quantile binning."""
        log_progress("Calculating RFM scores...")
        
        n_quantiles = self.config.n_quantiles
        
        # Recency score (lower recency = better = higher score)
        try:
            df["r_score"] = pd.qcut(
                df["recency"].rank(method="first"),
                q=n_quantiles,
                labels=self.config.recency_labels
            ).astype(int)
        except ValueError:
            # Fallback if not enough unique values
            df["r_score"] = 3
        
        # Frequency score (higher frequency = higher score)
        try:
            if df["frequency"].nunique() <= 1:
                df["f_score"] = 3
            else:
                df["f_score"] = pd.qcut(
                    df["frequency"].rank(method="first"),
                    q=n_quantiles,
                    labels=self.config.frequency_labels,
                    duplicates="drop"
                ).astype(int)
        except ValueError:
            df["f_score"] = 3
        
        # Monetary score (higher monetary = higher score)
        try:
            if df["monetary"].nunique() <= 1:
                df["m_score"] = 3
            else:
                df["m_score"] = pd.qcut(
                    df["monetary"].rank(method="first"),
                    q=n_quantiles,
                    labels=self.config.monetary_labels,
                    duplicates="drop"
                ).astype(int)
        except ValueError:
            df["m_score"] = 3
        
        return df
    
    def _calculate_combined_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate combined RFM score."""
        log_progress("Calculating combined RFM score...")
        
        # RFM string score (e.g., "555", "321")
        df["rfm_score_str"] = (
            df["r_score"].astype(str) + 
            df["f_score"].astype(str) + 
            df["m_score"].astype(str)
        )
        
        # Numeric combined score (weighted average)
        df["rfm_score"] = (
            df["r_score"] * 0.25 + 
            df["f_score"] * 0.35 + 
            df["m_score"] * 0.40
        ).round(2)
        
        return df
    
    def _assign_segments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assign customer segments based on RFM scores."""
        log_progress("Assigning customer segments...")
        
        def get_segment(row: pd.Series) -> str:
            r, f, m = row["r_score"], row["f_score"], row["m_score"]
            
            for segment, rules in self.config.segment_rules.items():
                match = True
                
                if "r_min" in rules and r < rules["r_min"]:
                    match = False
                if "r_max" in rules and r > rules["r_max"]:
                    match = False
                if "f_min" in rules and f < rules["f_min"]:
                    match = False
                if "f_max" in rules and f > rules["f_max"]:
                    match = False
                if "m_min" in rules and m < rules["m_min"]:
                    match = False
                if "m_max" in rules and m > rules["m_max"]:
                    match = False
                
                if match:
                    return segment
            
            return "Other"
        
        df["rfm_segment"] = df.apply(get_segment, axis=1)
        
        return df
    
    def _calculate_enhanced_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate enhanced RFM metrics."""
        log_progress("Calculating enhanced metrics...")
        
        # Average Order Value
        df["avg_order_value"] = safe_divide(
            df["monetary"],
            df["frequency"],
            fill_value=0
        ).round(2)
        
        # Monetary percentile rank (0-100)
        df["monetary_rank"] = calculate_percentile_rank(df["monetary"]).round(2)
        
        # Frequency percentile rank
        df["frequency_rank"] = calculate_percentile_rank(df["frequency"]).round(2)
        
        # Recency percentile rank (inverted - lower recency is better)
        df["recency_rank"] = (100 - calculate_percentile_rank(df["recency"])).round(2)
        
        # Customer value tier
        try:
            df["value_tier"] = pd.qcut(
                df["monetary_rank"],
                q=4,
                labels=["Bronze", "Silver", "Gold", "Platinum"],
                duplicates="drop"
            )
        except ValueError:
            df["value_tier"] = "Silver"
        
        return df
    
    def get_segment_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get summary statistics per RFM segment."""
        summary = df.groupby("rfm_segment").agg({
            "customer_id": "count",
            "recency": ["mean", "median"],
            "frequency": ["mean", "median", "sum"],
            "monetary": ["mean", "median", "sum"],
            "avg_order_value": "mean",
            "rfm_score": "mean",
        }).round(2)
        
        summary.columns = ["_".join(col).strip("_") for col in summary.columns]
        summary = summary.rename(columns={"customer_id_count": "customer_count"})
        
        total_customers = summary["customer_count"].sum()
        summary["customer_pct"] = (summary["customer_count"] / total_customers * 100).round(2)
        
        total_revenue = summary["monetary_sum"].sum()
        summary["revenue_pct"] = (summary["monetary_sum"] / total_revenue * 100).round(2)
        
        return summary.sort_values("monetary_sum", ascending=False).reset_index()
