"""
RFM Data Loader

Module untuk memuat dan menggabungkan data dari hasil feature engineering
untuk digunakan dalam RFM modeling (Clustering, Churn, CLV).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import warnings

from config.rfm_config import RFMModelConfig


class RFMDataLoader:
    """
    Data loader untuk RFM Modeling
    
    Memuat data dari output feature engineering:
    - rfm_features.csv
    - behavioral_features.csv
    - temporal_features.csv
    - customer_features.csv (master)
    """
    
    def __init__(self, config: RFMModelConfig):
        self.config = config
        self.data_cache: Dict[str, pd.DataFrame] = {}
        
    def _safe_load_csv(self, filepath: Path, file_description: str) -> Optional[pd.DataFrame]:
        """
        Safely load CSV file with proper error handling
        
        Args:
            filepath: Path to CSV file
            file_description: Description for error messages
            
        Returns:
            DataFrame or None if file not found
        """
        if not filepath.exists():
            if self.config.verbose:
                print(f"[RFMDataLoader] WARNING: {file_description} not found at {filepath}")
            return None
        
        try:
            df = pd.read_csv(filepath)
            if self.config.verbose:
                print(f"[RFMDataLoader] Loaded {file_description}: {len(df)} records")
            return df
        except Exception as e:
            if self.config.verbose:
                print(f"[RFMDataLoader] ERROR loading {file_description}: {e}")
            return None
        
    def load_rfm_features(self) -> pd.DataFrame:
        """Load RFM features dari feature engineering output"""
        if "rfm_features" in self.data_cache:
            return self.data_cache["rfm_features"]
        
        filepath = self.config.get_input_path("rfm_features")
        
        if self.config.verbose:
            print(f"[RFMDataLoader] Loading RFM features from {filepath}")
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"RFM features file not found: {filepath}\n"
                f"Please ensure feature engineering output is in: {self.config.base_input_path}"
            )
        
        df = pd.read_csv(filepath)
        self.data_cache["rfm_features"] = df
        
        if self.config.verbose:
            print(f"[RFMDataLoader] Loaded {len(df)} records with columns: {list(df.columns)}")
        
        return df
    
    def load_behavioral_features(self) -> Optional[pd.DataFrame]:
        """Load behavioral features"""
        if "behavioral_features" in self.data_cache:
            return self.data_cache["behavioral_features"]
        
        filepath = self.config.get_input_path("behavioral_features")
        df = self._safe_load_csv(filepath, "Behavioral features")
        
        if df is not None:
            self.data_cache["behavioral_features"] = df
        
        return df
    
    def load_temporal_features(self) -> Optional[pd.DataFrame]:
        """Load temporal features"""
        if "temporal_features" in self.data_cache:
            return self.data_cache["temporal_features"]
        
        filepath = self.config.get_input_path("temporal_features")
        df = self._safe_load_csv(filepath, "Temporal features")
        
        if df is not None:
            self.data_cache["temporal_features"] = df
        
        return df
    
    def load_customer_features(self) -> pd.DataFrame:
        """Load master customer features (gabungan semua features)"""
        if "customer_features" in self.data_cache:
            return self.data_cache["customer_features"]
        
        filepath = self.config.get_input_path("customer_features")
        
        if self.config.verbose:
            print(f"[RFMDataLoader] Loading customer features from {filepath}")
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"Customer features file not found: {filepath}\n"
                f"Please ensure feature engineering output is in: {self.config.base_input_path}"
            )
        
        df = pd.read_csv(filepath)
        self.data_cache["customer_features"] = df
        
        return df
    
    def load_all_features(self) -> pd.DataFrame:
        """
        Load dan merge semua features menjadi satu DataFrame
        
        Returns:
            DataFrame dengan semua features untuk modeling
        """
        if self.config.verbose:
            print("[RFMDataLoader] Loading all feature datasets...")
        
        # Load customer_features sebagai master (sudah berisi semua)
        master_df = self.load_customer_features()
        
        if self.config.verbose:
            print(f"[RFMDataLoader] Master dataset: {len(master_df)} customers, {len(master_df.columns)} features")
        
        return master_df
    
    def prepare_clustering_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data untuk clustering
        
        Returns:
            Tuple of (features DataFrame, customer IDs)
        """
        df = self.load_all_features()
        
        # Select clustering features
        feature_cols = self.config.clustering.clustering_features
        available_cols = [col for col in feature_cols if col in df.columns]
        
        if not available_cols:
            raise ValueError(
                f"None of the required clustering features found in data.\n"
                f"Required: {feature_cols}\n"
                f"Available: {list(df.columns)}"
            )
        
        if self.config.verbose:
            print(f"[RFMDataLoader] Clustering features available: {available_cols}")
            missing = set(feature_cols) - set(available_cols)
            if missing:
                print(f"[RFMDataLoader] Warning: Missing features: {missing}")
        
        customer_id_col = self.config.column_mapping.get("customer_id", "customer_id")
        
        if customer_id_col not in df.columns:
            print(f"[RFMDataLoader] Warning: customer_id column '{customer_id_col}' not found, using index")
            customer_ids = pd.Series(df.index, name="customer_id")
        else:
            customer_ids = df[customer_id_col]
        
        features_df = df[available_cols].copy()
        
        # Handle missing values
        features_df = features_df.fillna(features_df.median())
        
        if features_df.isna().all().all():
            raise ValueError("All feature values are NaN after loading. Please check your data.")
        
        return features_df, customer_ids
    
    def prepare_churn_data(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare data untuk churn prediction
        
        Returns:
            Tuple of (features DataFrame, target Series, customer IDs)
        """
        df = self.load_all_features()
        
        # Create churn target berdasarkan recency threshold
        recency_col = self.config.column_mapping.get("recency", "recency")
        threshold = self.config.churn.churn_threshold_days
        
        # Jika sudah ada churn_risk, gunakan itu
        if "churn_risk" in df.columns:
            # Convert churn_risk (High/Medium/Low) ke binary
            df["is_churned"] = df["churn_risk"].apply(
                lambda x: 1 if str(x).lower() == "high" else 0
            )
        elif recency_col in df.columns:
            # Buat churn label berdasarkan recency
            df["is_churned"] = (df[recency_col] > threshold).astype(int)
        else:
            raise ValueError(
                f"Cannot create churn target. Neither 'churn_risk' nor '{recency_col}' found in data.\n"
                f"Available columns: {list(df.columns)}"
            )
        
        # Select features
        feature_cols = self.config.churn.churn_features
        available_cols = [col for col in feature_cols if col in df.columns]
        
        if not available_cols:
            raise ValueError(
                f"None of the required churn features found in data.\n"
                f"Required: {feature_cols}\n"
                f"Available: {list(df.columns)}"
            )
        
        if self.config.verbose:
            print(f"[RFMDataLoader] Churn features available: {available_cols}")
            print(f"[RFMDataLoader] Churn distribution: {df['is_churned'].value_counts().to_dict()}")
        
        customer_id_col = self.config.column_mapping.get("customer_id", "customer_id")
        if customer_id_col not in df.columns:
            customer_ids = pd.Series(df.index, name="customer_id")
        else:
            customer_ids = df[customer_id_col]
        
        features_df = df[available_cols].copy()
        target = df["is_churned"]
        
        # Handle missing values
        features_df = features_df.fillna(features_df.median())
        
        return features_df, target, customer_ids
    
    def prepare_clv_data(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare data untuk CLV prediction
        
        Returns:
            Tuple of (features DataFrame, target Series (monetary), customer IDs)
        """
        df = self.load_all_features()
        
        # Target: monetary value (atau bisa dihitung CLV)
        monetary_col = self.config.column_mapping.get("monetary", "monetary")
        
        if monetary_col not in df.columns:
            raise ValueError(
                f"Monetary column '{monetary_col}' not found in data.\n"
                f"Available columns: {list(df.columns)}"
            )
        
        # Calculate simple CLV = monetary * expected_purchases_next_year
        if "purchase_velocity" in df.columns and df["purchase_velocity"].notna().any():
            # CLV = avg_transaction_value * expected_annual_purchases
            avg_tx_col = "avg_transaction_value" if "avg_transaction_value" in df.columns else monetary_col
            df["clv_target"] = df[avg_tx_col] * df["purchase_velocity"] * 12
            df["clv_target"] = df["clv_target"].fillna(df[monetary_col])
        else:
            # Use monetary as proxy for CLV
            df["clv_target"] = df[monetary_col]
        
        # Select features
        feature_cols = self.config.clv.clv_features
        available_cols = [col for col in feature_cols if col in df.columns]
        
        if not available_cols:
            raise ValueError(
                f"None of the required CLV features found in data.\n"
                f"Required: {feature_cols}\n"
                f"Available: {list(df.columns)}"
            )
        
        if self.config.verbose:
            print(f"[RFMDataLoader] CLV features available: {available_cols}")
            print(f"[RFMDataLoader] CLV target stats: mean={df['clv_target'].mean():.2f}, median={df['clv_target'].median():.2f}")
        
        customer_id_col = self.config.column_mapping.get("customer_id", "customer_id")
        if customer_id_col not in df.columns:
            customer_ids = pd.Series(df.index, name="customer_id")
        else:
            customer_ids = df[customer_id_col]
        
        features_df = df[available_cols].copy()
        target = df["clv_target"]
        
        # Handle missing values
        features_df = features_df.fillna(features_df.median())
        target = target.fillna(target.median())
        
        return features_df, target, customer_ids
    
    def get_data_summary(self) -> Dict:
        """Get summary statistik dari loaded data"""
        try:
            df = self.load_all_features()
        except FileNotFoundError:
            return {"error": "Data files not found"}
        
        summary = {
            "total_customers": len(df),
            "total_features": len(df.columns),
            "rfm_segments": df["rfm_segment"].value_counts().to_dict() if "rfm_segment" in df.columns else {},
            "value_tiers": df["value_tier"].value_counts().to_dict() if "value_tier" in df.columns else {},
            "churn_risk": df["churn_risk"].value_counts().to_dict() if "churn_risk" in df.columns else {},
        }
        
        return summary
    
    def clear_cache(self):
        """Clear data cache"""
        self.data_cache.clear()
        if self.config.verbose:
            print("[RFMDataLoader] Cache cleared")
