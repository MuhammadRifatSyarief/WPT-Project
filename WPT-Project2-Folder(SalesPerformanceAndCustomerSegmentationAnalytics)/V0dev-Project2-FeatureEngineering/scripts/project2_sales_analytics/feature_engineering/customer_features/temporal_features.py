"""
Temporal Feature Extractor

Extract time-based patterns from customer transactions.

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
from typing import Dict, List, Optional
from datetime import datetime

from config.feature_config import TemporalConfig
from utils.feature_utils import (
    safe_divide,
    log_progress,
    validate_dataframe,
)


class TemporalFeatureExtractor:
    """
    Extract temporal/time-based features from transaction data.
    
    Features extracted:
    - Day patterns: preferred_day_of_week, weekend_purchase_ratio
    - Seasonal patterns: preferred_quarter, seasonal_variation
    - Lifecycle: customer_tenure, churn_risk
    """
    
    def __init__(self, config: Optional[TemporalConfig] = None):
        """Initialize Temporal Feature Extractor."""
        self.config = config or TemporalConfig()
        
    def extract(
        self,
        sales_details: pd.DataFrame,
        customer_id_col: str = "customer_id",
        date_col: str = "transaction_date",
        amount_col: str = "total_amount",
    ) -> pd.DataFrame:
        """
        Extract temporal features from transaction data.
        
        Parameters
        ----------
        sales_details : pd.DataFrame
            Transaction-level data
        customer_id_col : str
            Column name for customer ID
        date_col : str
            Column name for transaction date
        amount_col : str
            Column name for transaction amount
            
        Returns
        -------
        pd.DataFrame
            Customer-level temporal features
        """
        log_progress("Starting temporal feature extraction...")
        
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
        
        # Extract date components
        df["day_of_week"] = df[date_col].dt.dayofweek
        df["day_name"] = df[date_col].dt.day_name()
        df["month"] = df[date_col].dt.month
        df["quarter"] = df[date_col].dt.quarter
        df["is_weekend"] = df["day_of_week"].isin(self.config.weekend_days).astype(int)
        
        # Extract feature groups
        day_patterns = self._extract_day_patterns(df, customer_id_col, amount_col)
        seasonal_patterns = self._extract_seasonal_patterns(df, customer_id_col, amount_col)
        lifecycle_features = self._extract_lifecycle_features(df, customer_id_col, date_col)
        
        # Merge all features
        result = day_patterns.merge(
            seasonal_patterns, on=customer_id_col, how="left"
        ).merge(
            lifecycle_features, on=customer_id_col, how="left"
        )
        
        log_progress(f"Temporal features extracted for {len(result)} customers")
        
        return result
    
    def _extract_day_patterns(
        self,
        df: pd.DataFrame,
        customer_id_col: str,
        amount_col: str,
    ) -> pd.DataFrame:
        """Extract day-of-week patterns."""
        log_progress("Extracting day patterns...")
        
        # Preferred day of week
        day_totals = df.groupby([customer_id_col, "day_name"]).size().reset_index(name="count")
        idx = day_totals.groupby(customer_id_col)["count"].idxmax()
        preferred_day = day_totals.loc[idx][[customer_id_col, "day_name"]].rename(
            columns={"day_name": "preferred_day_of_week"}
        )
        
        # Weekend vs weekday ratio
        weekend_stats = df.groupby(customer_id_col)["is_weekend"].agg(["sum", "count"]).reset_index()
        weekend_stats.columns = [customer_id_col, "weekend_purchases", "total_purchases_temp"]
        weekend_stats["weekend_purchase_ratio"] = safe_divide(
            weekend_stats["weekend_purchases"],
            weekend_stats["total_purchases_temp"],
            fill_value=0
        ).round(3)
        
        # Weekend spending ratio
        if amount_col in df.columns:
            weekend_spending = df.groupby([customer_id_col, "is_weekend"])[amount_col].sum().unstack(fill_value=0)
            weekend_spending.columns = ["weekday_spending", "weekend_spending"]
            weekend_spending["total_spending_temp"] = weekend_spending.sum(axis=1)
            weekend_spending["weekend_spending_ratio"] = safe_divide(
                weekend_spending["weekend_spending"],
                weekend_spending["total_spending_temp"],
                fill_value=0
            ).round(3)
            weekend_spending = weekend_spending[["weekend_spending_ratio"]].reset_index()
        else:
            weekend_spending = pd.DataFrame({
                customer_id_col: df[customer_id_col].unique(),
                "weekend_spending_ratio": 0
            })
        
        result = preferred_day.merge(
            weekend_stats[[customer_id_col, "weekend_purchase_ratio"]], on=customer_id_col, how="left"
        ).merge(
            weekend_spending, on=customer_id_col, how="left"
        )
        
        return result
    
    def _extract_seasonal_patterns(
        self,
        df: pd.DataFrame,
        customer_id_col: str,
        amount_col: str,
    ) -> pd.DataFrame:
        """Extract seasonal/quarterly patterns."""
        log_progress("Extracting seasonal patterns...")
        
        # Transactions per quarter
        quarter_counts = df.groupby([customer_id_col, "quarter"]).size().unstack(fill_value=0)
        quarter_counts.columns = [f"q{i}_count" for i in quarter_counts.columns]
        
        # Preferred quarter
        quarter_totals = df.groupby([customer_id_col, "quarter"]).size().reset_index(name="count")
        idx = quarter_totals.groupby(customer_id_col)["count"].idxmax()
        preferred_quarter = quarter_totals.loc[idx][[customer_id_col, "quarter"]].rename(
            columns={"quarter": "preferred_quarter"}
        )
        
        # Seasonal variation
        def calculate_quarterly_cv(row):
            q_cols = [col for col in row.index if col.startswith("q") and col.endswith("_count")]
            values = row[q_cols].values
            if values.mean() == 0:
                return 0
            return round(values.std() / values.mean(), 3)
        
        quarter_counts_reset = quarter_counts.reset_index()
        quarter_counts_reset["seasonal_variation"] = quarter_counts_reset.apply(calculate_quarterly_cv, axis=1)
        
        # Merge
        result = quarter_counts_reset.merge(
            preferred_quarter, on=customer_id_col, how="left"
        )
        
        return result
    
    def _extract_lifecycle_features(
        self,
        df: pd.DataFrame,
        customer_id_col: str,
        date_col: str,
    ) -> pd.DataFrame:
        """Extract customer lifecycle features."""
        log_progress("Extracting lifecycle features...")
        
        reference_date = self.config.reference_date or datetime.now()
        
        lifecycle = df.groupby(customer_id_col)[date_col].agg(["min", "max", "count"]).reset_index()
        lifecycle.columns = [customer_id_col, "first_purchase_date", "last_purchase_date", "total_transactions"]
        
        # Customer tenure
        lifecycle["customer_tenure_days"] = (reference_date - lifecycle["first_purchase_date"]).dt.days
        
        # Recency
        lifecycle["recency_days"] = (reference_date - lifecycle["last_purchase_date"]).dt.days
        
        # Active period
        lifecycle["active_period_days"] = (
            lifecycle["last_purchase_date"] - lifecycle["first_purchase_date"]
        ).dt.days
        
        # Purchase velocity
        lifecycle["purchase_velocity"] = safe_divide(
            lifecycle["total_transactions"],
            lifecycle["customer_tenure_days"] / 30,
            fill_value=0
        ).round(3)
        
        # Lifecycle stage
        lifecycle["lifecycle_stage"] = pd.cut(
            lifecycle["customer_tenure_days"],
            bins=[-np.inf, 30, 90, 180, 365, np.inf],
            labels=["New", "Developing", "Established", "Mature", "Veteran"]
        )
        
        # Churn risk
        avg_interval = safe_divide(
            lifecycle["active_period_days"],
            lifecycle["total_transactions"] - 1,
            fill_value=365
        )
        lifecycle["expected_days_to_purchase"] = avg_interval
        lifecycle["days_overdue"] = lifecycle["recency_days"] - lifecycle["expected_days_to_purchase"]
        lifecycle["churn_risk"] = pd.cut(
            lifecycle["days_overdue"],
            bins=[-np.inf, 0, 30, 60, np.inf],
            labels=["Active", "At Risk", "Dormant", "Churned"]
        )
        
        return lifecycle
