"""
Outlier Handler Module

New preprocessing module untuk handle outliers dan skewed data:
- IQR-based clipping
- Percentile-based clipping
- Log transformation
- Winsorization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Literal
from scipy import stats


class OutlierHandler:
    """
    Comprehensive outlier detection dan handling
    
    Methods:
    - IQR clipping
    - Percentile clipping
    - Log transformation
    - Winsorization
    - Z-score detection
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize OutlierHandler
        
        Args:
            verbose: Print progress messages
        """
        self.verbose = verbose
        self.bounds: Dict[str, Dict[str, float]] = {}
        self.transformations: Dict[str, str] = {}
        self.outlier_counts: Dict[str, int] = {}
    
    def clip_by_iqr(
        self,
        X: pd.DataFrame,
        columns: Optional[List[str]] = None,
        iqr_multiplier: float = 1.5
    ) -> pd.DataFrame:
        """
        Clip outliers menggunakan IQR method
        
        Args:
            X: DataFrame dengan features
            columns: Columns untuk di-clip (None = semua numeric)
            iqr_multiplier: Multiplier untuk IQR range (default 1.5)
            
        Returns:
            DataFrame dengan clipped values
        """
        X_clipped = X.copy()
        
        if columns is None:
            columns = X.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in X.columns:
                continue
            
            Q1 = X[col].quantile(0.25)
            Q3 = X[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - iqr_multiplier * IQR
            upper_bound = Q3 + iqr_multiplier * IQR
            
            # Count outliers
            outliers = ((X[col] < lower_bound) | (X[col] > upper_bound)).sum()
            self.outlier_counts[col] = outliers
            
            # Clip
            X_clipped[col] = X[col].clip(lower=lower_bound, upper=upper_bound)
            
            # Store bounds
            self.bounds[col] = {
                "method": "iqr",
                "lower": lower_bound,
                "upper": upper_bound,
                "Q1": Q1,
                "Q3": Q3,
                "IQR": IQR
            }
            
            if self.verbose and outliers > 0:
                print(f"[OutlierHandler] {col}: Clipped {outliers} outliers using IQR "
                      f"(bounds: [{lower_bound:.2f}, {upper_bound:.2f}])")
        
        return X_clipped
    
    def clip_by_percentile(
        self,
        X: pd.DataFrame,
        columns: Optional[List[str]] = None,
        lower_percentile: float = 1,
        upper_percentile: float = 99
    ) -> pd.DataFrame:
        """
        Clip outliers menggunakan percentiles
        
        Args:
            X: DataFrame dengan features
            columns: Columns untuk di-clip
            lower_percentile: Lower percentile threshold (0-100)
            upper_percentile: Upper percentile threshold (0-100)
            
        Returns:
            DataFrame dengan clipped values
        """
        X_clipped = X.copy()
        
        if columns is None:
            columns = X.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in X.columns:
                continue
            
            lower_bound = X[col].quantile(lower_percentile / 100)
            upper_bound = X[col].quantile(upper_percentile / 100)
            
            # Count outliers
            outliers = ((X[col] < lower_bound) | (X[col] > upper_bound)).sum()
            self.outlier_counts[col] = outliers
            
            # Clip
            X_clipped[col] = X[col].clip(lower=lower_bound, upper=upper_bound)
            
            # Store bounds
            self.bounds[col] = {
                "method": "percentile",
                "lower": lower_bound,
                "upper": upper_bound,
                "lower_pct": lower_percentile,
                "upper_pct": upper_percentile
            }
            
            if self.verbose and outliers > 0:
                print(f"[OutlierHandler] {col}: Clipped {outliers} outliers using percentiles "
                      f"(P{lower_percentile}-P{upper_percentile}: [{lower_bound:.2f}, {upper_bound:.2f}])")
        
        return X_clipped
    
    def log_transform(
        self,
        X: pd.DataFrame,
        columns: Optional[List[str]] = None,
        add_constant: float = 1.0
    ) -> pd.DataFrame:
        """
        Apply log transformation untuk handle skewed data
        
        Args:
            X: DataFrame dengan features
            columns: Columns untuk transform
            add_constant: Constant to add before log (untuk handle zeros)
            
        Returns:
            DataFrame dengan log-transformed values
        """
        X_transformed = X.copy()
        
        if columns is None:
            # Auto-detect skewed columns
            columns = []
            for col in X.select_dtypes(include=[np.number]).columns:
                skewness = X[col].skew()
                if abs(skewness) > 1.0:  # Highly skewed
                    columns.append(col)
        
        for col in columns:
            if col not in X.columns:
                continue
            
            # Ensure positive values
            min_val = X[col].min()
            if min_val <= 0:
                shift = abs(min_val) + add_constant
            else:
                shift = add_constant
            
            # Apply log transformation
            X_transformed[col] = np.log(X[col] + shift)
            
            self.transformations[col] = f"log(x + {shift})"
            
            if self.verbose:
                original_skew = X[col].skew()
                new_skew = X_transformed[col].skew()
                print(f"[OutlierHandler] {col}: Log transformed (skewness: {original_skew:.2f} → {new_skew:.2f})")
        
        return X_transformed
    
    def winsorize(
        self,
        X: pd.DataFrame,
        columns: Optional[List[str]] = None,
        limits: Tuple[float, float] = (0.05, 0.05)
    ) -> pd.DataFrame:
        """
        Winsorize outliers (replace dengan boundary values)
        
        Args:
            X: DataFrame dengan features
            columns: Columns untuk winsorize
            limits: (lower, upper) percentage to winsorize (e.g., (0.05, 0.05) = 5% each tail)
            
        Returns:
            DataFrame dengan winsorized values
        """
        X_winsorized = X.copy()
        
        if columns is None:
            columns = X.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in X.columns:
                continue
            
            winsorized = stats.mstats.winsorize(X[col].values, limits=limits)
            X_winsorized[col] = winsorized
            
            # Count modified values
            modified = (X[col].values != winsorized).sum()
            self.outlier_counts[col] = modified
            
            if self.verbose and modified > 0:
                print(f"[OutlierHandler] {col}: Winsorized {modified} values (limits: {limits})")
        
        return X_winsorized
    
    def detect_outliers_zscore(
        self,
        X: pd.DataFrame,
        columns: Optional[List[str]] = None,
        threshold: float = 3.0
    ) -> Dict[str, np.ndarray]:
        """
        Detect outliers menggunakan Z-score method
        
        Args:
            X: DataFrame dengan features
            columns: Columns untuk check
            threshold: Z-score threshold (default 3.0)
            
        Returns:
            Dictionary dengan boolean masks untuk outliers
        """
        if columns is None:
            columns = X.select_dtypes(include=[np.number]).columns.tolist()
        
        outlier_masks = {}
        
        for col in columns:
            if col not in X.columns:
                continue
            
            z_scores = np.abs(stats.zscore(X[col].fillna(X[col].mean())))
            is_outlier = z_scores > threshold
            
            outlier_masks[col] = is_outlier
            outlier_count = is_outlier.sum()
            
            if self.verbose:
                pct = (outlier_count / len(X)) * 100
                print(f"[OutlierHandler] {col}: Found {outlier_count} outliers via Z-score ({pct:.2f}%)")
        
        return outlier_masks
    
    def get_outlier_summary(self) -> pd.DataFrame:
        """
        Get summary of outlier handling
        
        Returns:
            DataFrame dengan summary statistics
        """
        summary_data = []
        
        for col, bounds in self.bounds.items():
            row = {
                "feature": col,
                "method": bounds["method"],
                "lower_bound": bounds.get("lower"),
                "upper_bound": bounds.get("upper"),
                "outliers_handled": self.outlier_counts.get(col, 0),
                "transformation": self.transformations.get(col, "none")
            }
            summary_data.append(row)
        
        return pd.DataFrame(summary_data)
    
    def auto_handle_outliers(
        self,
        X: pd.DataFrame,
        method: Literal["iqr", "percentile", "winsorize"] = "iqr",
        log_transform_skewed: bool = True,
        skew_threshold: float = 2.0
    ) -> pd.DataFrame:
        """
        Automatically handle outliers dengan best practices
        
        Args:
            X: DataFrame dengan features
            method: Method untuk clip outliers
            log_transform_skewed: Apply log transform untuk highly skewed data
            skew_threshold: Threshold untuk determine skewed features
            
        Returns:
            DataFrame dengan handled outliers
        """
        X_processed = X.copy()
        
        if self.verbose:
            print("[OutlierHandler] Auto-handling outliers...")
        
        # Step 1: Detect dan transform skewed features
        if log_transform_skewed:
            skewed_cols = []
            for col in X.select_dtypes(include=[np.number]).columns:
                skewness = abs(X[col].skew())
                if skewness > skew_threshold and X[col].min() >= 0:
                    skewed_cols.append(col)
            
            if skewed_cols:
                if self.verbose:
                    print(f"[OutlierHandler] Applying log transform to {len(skewed_cols)} skewed features")
                X_processed = self.log_transform(X_processed, columns=skewed_cols)
        
        # Step 2: Clip outliers
        if method == "iqr":
            X_processed = self.clip_by_iqr(X_processed)
        elif method == "percentile":
            X_processed = self.clip_by_percentile(X_processed, lower_percentile=1, upper_percentile=99)
        elif method == "winsorize":
            X_processed = self.winsorize(X_processed, limits=(0.05, 0.05))
        
        if self.verbose:
            print(f"[OutlierHandler] Outlier handling complete using {method} method")
        
        return X_processed
