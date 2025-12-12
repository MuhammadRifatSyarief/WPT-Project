"""
Feature Selector Module

Module untuk pemilihan features berdasarkan berbagai kriteria:
- Correlation analysis
- Variance threshold
- Feature importance
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.feature_selection import VarianceThreshold
from scipy import stats


class FeatureSelector:
    """
    Feature selector untuk memilih features terbaik untuk modeling
    
    Methods:
    - select_by_variance: Hapus features dengan variance rendah
    - select_by_correlation: Hapus features dengan correlation tinggi
    - select_by_list: Pilih features dari list yang ditentukan
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.selected_features: List[str] = []
        self.removed_features: List[str] = []
        self.correlation_matrix: Optional[pd.DataFrame] = None
    
    def select_by_variance(
        self, 
        X: pd.DataFrame, 
        threshold: float = 0.01
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Remove features dengan variance di bawah threshold
        
        Args:
            X: DataFrame dengan features
            threshold: Minimum variance threshold
            
        Returns:
            Tuple of (filtered DataFrame, removed feature names)
        """
        selector = VarianceThreshold(threshold=threshold)
        
        # Fit dan transform
        X_filtered = selector.fit_transform(X)
        
        # Get feature names yang tersisa
        mask = selector.get_support()
        selected_cols = X.columns[mask].tolist()
        removed_cols = X.columns[~mask].tolist()
        
        result_df = pd.DataFrame(X_filtered, columns=selected_cols, index=X.index)
        
        if self.verbose:
            print(f"[FeatureSelector] Variance filter: kept {len(selected_cols)}, removed {len(removed_cols)}")
            if removed_cols:
                print(f"[FeatureSelector] Removed low variance: {removed_cols}")
        
        self.removed_features.extend(removed_cols)
        
        return result_df, removed_cols
    
    def select_by_correlation(
        self,
        X: pd.DataFrame,
        threshold: float = 0.9,
        method: str = "pearson"
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Remove features dengan correlation tinggi (multicollinearity)
        
        Args:
            X: DataFrame dengan features
            threshold: Maximum correlation threshold
            method: Correlation method ('pearson', 'spearman')
            
        Returns:
            Tuple of (filtered DataFrame, removed feature names)
        """
        # Calculate correlation matrix
        self.correlation_matrix = X.corr(method=method).abs()
        
        # Upper triangle matrix
        upper = self.correlation_matrix.where(
            np.triu(np.ones(self.correlation_matrix.shape), k=1).astype(bool)
        )
        
        # Find features dengan correlation > threshold
        to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
        
        # Keep features yang tidak di-drop
        selected_cols = [col for col in X.columns if col not in to_drop]
        result_df = X[selected_cols].copy()
        
        if self.verbose:
            print(f"[FeatureSelector] Correlation filter (>{threshold}): kept {len(selected_cols)}, removed {len(to_drop)}")
            if to_drop:
                print(f"[FeatureSelector] Removed high correlation: {to_drop}")
        
        self.removed_features.extend(to_drop)
        
        return result_df, to_drop
    
    def select_by_list(
        self,
        X: pd.DataFrame,
        feature_list: List[str]
    ) -> pd.DataFrame:
        """
        Select features dari list yang ditentukan
        
        Args:
            X: DataFrame dengan features
            feature_list: List of feature names to select
            
        Returns:
            DataFrame dengan selected features
        """
        available = [f for f in feature_list if f in X.columns]
        missing = [f for f in feature_list if f not in X.columns]
        
        if self.verbose:
            print(f"[FeatureSelector] Selected {len(available)} features from list")
            if missing:
                print(f"[FeatureSelector] Warning - Missing features: {missing}")
        
        self.selected_features = available
        
        return X[available].copy()
    
    def analyze_feature_correlations(
        self,
        X: pd.DataFrame,
        target: Optional[pd.Series] = None
    ) -> Dict:
        """
        Analyze correlations antar features dan dengan target
        
        Args:
            X: DataFrame dengan features
            target: Optional target variable
            
        Returns:
            Dictionary dengan correlation analysis
        """
        analysis = {}
        
        # Feature-feature correlations
        corr_matrix = X.corr()
        analysis["correlation_matrix"] = corr_matrix
        
        # Find highly correlated pairs
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if abs(corr_matrix.iloc[i, j]) > 0.7:
                    high_corr_pairs.append({
                        "feature_1": corr_matrix.columns[i],
                        "feature_2": corr_matrix.columns[j],
                        "correlation": corr_matrix.iloc[i, j]
                    })
        
        analysis["high_correlation_pairs"] = sorted(
            high_corr_pairs,
            key=lambda x: abs(x["correlation"]),
            reverse=True
        )
        
        # Target correlations if provided
        if target is not None:
            target_corr = {}
            for col in X.columns:
                corr, pvalue = stats.pearsonr(X[col].fillna(0), target.fillna(0))
                target_corr[col] = {
                    "correlation": corr,
                    "p_value": pvalue,
                    "significant": pvalue < 0.05
                }
            
            analysis["target_correlations"] = dict(
                sorted(target_corr.items(), key=lambda x: abs(x[1]["correlation"]), reverse=True)
            )
        
        return analysis
    
    def get_feature_statistics(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Get comprehensive statistics untuk setiap feature
        
        Args:
            X: DataFrame dengan features
            
        Returns:
            DataFrame dengan statistics per feature
        """
        stats_list = []
        
        for col in X.columns:
            col_stats = {
                "feature": col,
                "dtype": str(X[col].dtype),
                "count": X[col].count(),
                "missing": X[col].isna().sum(),
                "missing_pct": X[col].isna().mean() * 100,
                "unique": X[col].nunique(),
                "mean": X[col].mean() if np.issubdtype(X[col].dtype, np.number) else None,
                "std": X[col].std() if np.issubdtype(X[col].dtype, np.number) else None,
                "min": X[col].min() if np.issubdtype(X[col].dtype, np.number) else None,
                "max": X[col].max() if np.issubdtype(X[col].dtype, np.number) else None,
                "variance": X[col].var() if np.issubdtype(X[col].dtype, np.number) else None,
                "skewness": X[col].skew() if np.issubdtype(X[col].dtype, np.number) else None
            }
            stats_list.append(col_stats)
        
        return pd.DataFrame(stats_list)
