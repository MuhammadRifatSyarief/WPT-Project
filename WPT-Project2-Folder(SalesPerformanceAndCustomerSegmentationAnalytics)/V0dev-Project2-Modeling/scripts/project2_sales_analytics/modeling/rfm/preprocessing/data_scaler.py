"""
Data Scaler Module

Module untuk scaling dan normalisasi data sebelum modeling.
Mendukung StandardScaler, MinMaxScaler, dan RobustScaler.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, List
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
import joblib
from pathlib import Path


class DataScaler:
    """
    Data scaler untuk normalisasi features
    
    Supports:
    - StandardScaler: Mean=0, Std=1 (default untuk clustering)
    - MinMaxScaler: Range [0, 1]
    - RobustScaler: Robust terhadap outliers
    """
    
    SCALER_TYPES = {
        "standard": StandardScaler,
        "minmax": MinMaxScaler,
        "robust": RobustScaler
    }
    
    def __init__(self, scaler_type: str = "standard", verbose: bool = True):
        """
        Initialize DataScaler
        
        Args:
            scaler_type: Tipe scaler ('standard', 'minmax', 'robust')
            verbose: Print progress messages
        """
        self.scaler_type = scaler_type
        self.verbose = verbose
        self.scaler = None
        self.feature_names: List[str] = []
        self.is_fitted = False
        
        if scaler_type not in self.SCALER_TYPES:
            raise ValueError(f"Unknown scaler type: {scaler_type}. Use: {list(self.SCALER_TYPES.keys())}")
        
        self.scaler = self.SCALER_TYPES[scaler_type]()
        
        if self.verbose:
            print(f"[DataScaler] Initialized with {scaler_type} scaler")
    
    def fit(self, X: pd.DataFrame) -> "DataScaler":
        """
        Fit scaler pada data
        
        Args:
            X: DataFrame dengan features untuk di-fit
            
        Returns:
            self untuk chaining
        """
        self.feature_names = list(X.columns)
        self.scaler.fit(X)
        self.is_fitted = True
        
        if self.verbose:
            print(f"[DataScaler] Fitted on {len(self.feature_names)} features")
        
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data menggunakan fitted scaler
        
        Args:
            X: DataFrame untuk di-transform
            
        Returns:
            Scaled DataFrame
        """
        if not self.is_fitted:
            raise ValueError("Scaler belum di-fit. Panggil fit() terlebih dahulu.")
        
        scaled_values = self.scaler.transform(X)
        scaled_df = pd.DataFrame(
            scaled_values,
            columns=self.feature_names,
            index=X.index
        )
        
        if self.verbose:
            print(f"[DataScaler] Transformed {len(X)} records")
        
        return scaled_df
    
    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Fit dan transform dalam satu langkah
        
        Args:
            X: DataFrame untuk fit dan transform
            
        Returns:
            Scaled DataFrame
        """
        self.fit(X)
        return self.transform(X)
    
    def inverse_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Inverse transform scaled data ke original scale
        
        Args:
            X: Scaled DataFrame
            
        Returns:
            Original scale DataFrame
        """
        if not self.is_fitted:
            raise ValueError("Scaler belum di-fit.")
        
        original_values = self.scaler.inverse_transform(X)
        original_df = pd.DataFrame(
            original_values,
            columns=self.feature_names,
            index=X.index
        )
        
        return original_df
    
    def get_scaling_stats(self) -> Dict:
        """Get statistik scaling (mean, std untuk StandardScaler)"""
        if not self.is_fitted:
            return {}
        
        stats = {}
        
        if self.scaler_type == "standard":
            stats["mean"] = dict(zip(self.feature_names, self.scaler.mean_))
            stats["std"] = dict(zip(self.feature_names, self.scaler.scale_))
        elif self.scaler_type == "minmax":
            stats["min"] = dict(zip(self.feature_names, self.scaler.data_min_))
            stats["max"] = dict(zip(self.feature_names, self.scaler.data_max_))
        elif self.scaler_type == "robust":
            stats["center"] = dict(zip(self.feature_names, self.scaler.center_))
            stats["scale"] = dict(zip(self.feature_names, self.scaler.scale_))
        
        return stats
    
    def save(self, filepath: str):
        """Save scaler ke file"""
        save_data = {
            "scaler": self.scaler,
            "scaler_type": self.scaler_type,
            "feature_names": self.feature_names,
            "is_fitted": self.is_fitted
        }
        joblib.dump(save_data, filepath)
        
        if self.verbose:
            print(f"[DataScaler] Saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> "DataScaler":
        """Load scaler dari file"""
        save_data = joblib.load(filepath)
        
        instance = cls(scaler_type=save_data["scaler_type"], verbose=False)
        instance.scaler = save_data["scaler"]
        instance.feature_names = save_data["feature_names"]
        instance.is_fitted = save_data["is_fitted"]
        
        return instance
