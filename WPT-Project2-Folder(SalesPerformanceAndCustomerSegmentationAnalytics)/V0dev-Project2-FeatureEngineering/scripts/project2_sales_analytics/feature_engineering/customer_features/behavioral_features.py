"""
Behavioral Feature Extractor

Extract customer behavioral patterns from transaction history.

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

from config.feature_config import BehavioralConfig
from utils.feature_utils import (
    safe_divide,
    detect_outliers,
    calculate_coefficient_of_variation,
    validate_dataframe,
    log_progress,
)


class BehavioralFeatureExtractor:
    """
    Extract behavioral features from customer transaction data.
    
    Features extracted:
    - Purchase patterns: purchase_consistency, avg_days_between_purchases
    - Product preferences: product_diversity, category_concentration
    - Spending patterns: spending_volatility, trend_direction
    - Engagement metrics: engagement_score, loyalty_indicator
    """
    
    def __init__(self, config: Optional[BehavioralConfig] = None):
        """Initialize Behavioral Feature Extractor."""
        self.config = config or BehavioralConfig()
        
    def extract(
        self,
        sales_details: pd.DataFrame,
        sales_by_customer: Optional[pd.DataFrame] = None,
        customer_id_col: str = "customer_id",
        product_id_col: str = "product_id",
        category_col: str = "item_category_name",
        date_col: str = "transaction_date",
        amount_col: str = "total_amount",
        quantity_col: str = "quantity",
    ) -> pd.DataFrame:
        """
        Extract behavioral features from transaction-level data.
        
        Parameters
        ----------
        sales_details : pd.DataFrame
            Transaction-level sales data
        sales_by_customer : pd.DataFrame, optional
            Pre-aggregated customer data (not used currently)
        customer_id_col : str
            Column name for customer ID
        product_id_col : str
            Column name for product ID
        category_col : str
            Column name for product category
        date_col : str
            Column name for transaction date
        amount_col : str
            Column name for transaction amount
            
        Returns
        -------
        pd.DataFrame
            Customer-level behavioral features
        """
        log_progress("Starting behavioral feature extraction...")
        
        df = sales_details.copy()
        
        try:
            df[date_col] = pd.to_datetime(df[date_col])
        except Exception as e:
            log_progress(f"Warning: Could not convert {date_col} to datetime: {e}")
        
        # Extract feature groups
        purchase_patterns = self._extract_purchase_patterns(
            df, customer_id_col, date_col, amount_col
        )
        
        product_preferences = self._extract_product_preferences(
            df, customer_id_col, product_id_col, category_col
        )
        
        spending_patterns = self._extract_spending_patterns(
            df, customer_id_col, date_col, amount_col
        )
        
        # Merge all features
        result = purchase_patterns.merge(
            product_preferences, on=customer_id_col, how="left"
        ).merge(
            spending_patterns, on=customer_id_col, how="left"
        )
        
        # Calculate composite scores
        result = self._calculate_composite_scores(result)
        
        log_progress(f"Behavioral features extracted for {len(result)} customers")
        
        return result
    
    def _extract_purchase_patterns(
        self,
        df: pd.DataFrame,
        customer_id_col: str,
        date_col: str,
        amount_col: str,
    ) -> pd.DataFrame:
        """Extract purchase timing and consistency patterns."""
        log_progress("Extracting purchase patterns...")
        
        # Group by customer and sort by date
        customer_dates = df.groupby(customer_id_col)[date_col].agg(list).reset_index()
        customer_dates.columns = [customer_id_col, "purchase_dates"]
        
        def calculate_purchase_metrics(dates: List) -> Dict:
            dates = sorted(dates)
            n_purchases = len(dates)
            
            if n_purchases < 2:
                return {
                    "avg_days_between_purchases": None,
                    "purchase_consistency": None,
                    "days_since_first_purchase": (datetime.now() - dates[0]).days if dates else None,
                    "purchase_span_days": 0,
                }
            
            # Calculate intervals between purchases
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            
            avg_interval = np.mean(intervals)
            
            # Consistency (lower CV = more consistent)
            cv = calculate_coefficient_of_variation(pd.Series(intervals))
            consistency = 1 - min(cv, 1)
            
            return {
                "avg_days_between_purchases": round(avg_interval, 1),
                "purchase_consistency": round(consistency, 3),
                "days_since_first_purchase": (datetime.now() - dates[0]).days,
                "purchase_span_days": (dates[-1] - dates[0]).days,
            }
        
        metrics_df = customer_dates["purchase_dates"].apply(
            lambda x: pd.Series(calculate_purchase_metrics(x))
        )
        
        result = pd.concat([customer_dates[[customer_id_col]], metrics_df], axis=1)
        
        return result
    
    def _extract_product_preferences(
        self,
        df: pd.DataFrame,
        customer_id_col: str,
        product_id_col: str,
        category_col: str,
    ) -> pd.DataFrame:
        """Extract product and category preferences."""
        log_progress("Extracting product preferences...")
        
        # Product diversity
        product_diversity = df.groupby(customer_id_col)[product_id_col].nunique().reset_index()
        product_diversity.columns = [customer_id_col, "unique_products_bought"]
        
        result = product_diversity.copy()
        
        # Category preferences
        if category_col in df.columns:
            category_diversity = df.groupby(customer_id_col)[category_col].nunique().reset_index()
            category_diversity.columns = [customer_id_col, "unique_categories_bought"]
            
            # Most purchased category
            top_category = df.groupby([customer_id_col, category_col]).size().reset_index(name="count")
            idx = top_category.groupby(customer_id_col)["count"].idxmax()
            top_category = top_category.loc[idx][[customer_id_col, category_col]].rename(
                columns={category_col: "preferred_category"}
            )
            
            # Category concentration (HHI)
            category_counts = df.groupby([customer_id_col, category_col]).size().reset_index(name="count")
            total_by_customer = category_counts.groupby(customer_id_col)["count"].transform("sum")
            category_counts["share"] = category_counts["count"] / total_by_customer
            category_counts["share_squared"] = category_counts["share"] ** 2
            category_hhi = category_counts.groupby(customer_id_col)["share_squared"].sum().reset_index()
            category_hhi.columns = [customer_id_col, "category_concentration"]
            
            result = result.merge(
                category_diversity, on=customer_id_col, how="left"
            ).merge(
                top_category, on=customer_id_col, how="left"
            ).merge(
                category_hhi, on=customer_id_col, how="left"
            )
        else:
            result["unique_categories_bought"] = None
            result["preferred_category"] = None
            result["category_concentration"] = None
        
        # Product diversity classification
        low_thresh = self.config.low_diversity_threshold
        high_thresh = self.config.high_diversity_threshold
        
        result["product_diversity_level"] = pd.cut(
            result["unique_products_bought"],
            bins=[-np.inf, low_thresh, high_thresh, np.inf],
            labels=["Low", "Medium", "High"]
        )
        
        return result
    
    def _extract_spending_patterns(
        self,
        df: pd.DataFrame,
        customer_id_col: str,
        date_col: str,
        amount_col: str,
    ) -> pd.DataFrame:
        """Extract spending behavior patterns."""
        log_progress("Extracting spending patterns...")
        
        # Basic spending metrics
        spending_stats = df.groupby(customer_id_col).agg({
            amount_col: ["mean", "std", "min", "max", "sum", "count"]
        }).reset_index()
        
        spending_stats.columns = [
            customer_id_col, "avg_transaction_value", "transaction_value_std",
            "min_transaction_value", "max_transaction_value", 
            "total_spending", "transaction_count"
        ]
        
        # Fill NaN std with 0
        spending_stats["transaction_value_std"] = spending_stats["transaction_value_std"].fillna(0)
        
        # Spending volatility
        spending_stats["spending_volatility"] = safe_divide(
            spending_stats["transaction_value_std"],
            spending_stats["avg_transaction_value"],
            fill_value=0
        ).round(3)
        
        # Spending trend
        df_sorted = df.sort_values([customer_id_col, date_col])
        df_sorted["row_num"] = df_sorted.groupby(customer_id_col).cumcount() + 1
        df_sorted["total_rows"] = df_sorted.groupby(customer_id_col)[customer_id_col].transform("count")
        df_sorted["half"] = np.where(
            df_sorted["row_num"] <= df_sorted["total_rows"] / 2, 
            "first", "second"
        )
        
        half_spending = df_sorted.groupby([customer_id_col, "half"])[amount_col].mean().unstack()
        if "first" in half_spending.columns and "second" in half_spending.columns:
            half_spending["spending_trend"] = safe_divide(
                half_spending["second"] - half_spending["first"],
                half_spending["first"],
                fill_value=0
            ).round(3)
            half_spending = half_spending[["spending_trend"]].reset_index()
        else:
            half_spending = pd.DataFrame({
                customer_id_col: df[customer_id_col].unique(),
                "spending_trend": 0
            })
        
        result = spending_stats.merge(half_spending, on=customer_id_col, how="left")
        result["spending_trend"] = result["spending_trend"].fillna(0)
        
        # Trend direction
        result["trend_direction"] = pd.cut(
            result["spending_trend"],
            bins=[-np.inf, -0.1, 0.1, np.inf],
            labels=["Declining", "Stable", "Growing"]
        )
        
        return result
    
    def _calculate_composite_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate composite behavioral scores."""
        log_progress("Calculating composite scores...")
        
        # Engagement score (0-100)
        engagement_components = []
        
        if "purchase_consistency" in df.columns:
            consistency_score = df["purchase_consistency"].fillna(0) * 30
            engagement_components.append(consistency_score)
        
        if "unique_products_bought" in df.columns:
            diversity_score = df["unique_products_bought"].rank(pct=True) * 30
            engagement_components.append(diversity_score)
        
        if "total_spending" in df.columns:
            spending_score = df["total_spending"].rank(pct=True) * 40
            engagement_components.append(spending_score)
        
        if engagement_components:
            df["engagement_score"] = sum(engagement_components).round(2)
        else:
            df["engagement_score"] = 50
        
        # Loyalty indicator
        df["loyalty_indicator"] = "Low"
        
        if "purchase_consistency" in df.columns and "transaction_count" in df.columns:
            high_loyalty_mask = (
                (df["purchase_consistency"].fillna(0) > 0.5) & 
                (df["transaction_count"] >= self.config.min_transactions_for_consistency)
            )
            medium_loyalty_mask = (
                (df["purchase_consistency"].fillna(0) > 0.3) | 
                (df["transaction_count"] >= 2)
            )
            
            df.loc[medium_loyalty_mask, "loyalty_indicator"] = "Medium"
            df.loc[high_loyalty_mask, "loyalty_indicator"] = "High"
        
        return df
