"""
RFM Model Configuration

Konfigurasi untuk semua parameter model RFM:
- Clustering parameters
- Churn classification parameters
- CLV regression parameters
- Feature engineering parameters
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


RFM_DIR = Path(__file__).parent.parent  # scripts/project2_sales_analytics/modeling/rfm
MODELING_DIR = RFM_DIR.parent  # scripts/project2_sales_analytics/modeling
PROJECT_DIR = MODELING_DIR.parent  # scripts/project2_sales_analytics

DEFAULT_FEATURE_ENGINEERING_OUTPUT = PROJECT_DIR / "output" / "features" / "csv"


@dataclass
class ClusteringConfig:
    """Konfigurasi untuk Customer Clustering"""
    
    # K-Means parameters
    n_clusters: int = 3  # 3 kategori: High, Medium, Low
    algorithm: str = "kmeans"  # kmeans atau dbscan
    random_state: int = 42
    max_iter: int = 300
    n_init: int = 10
    
    # DBSCAN parameters (alternative)
    eps: float = 0.5
    min_samples: int = 5
    
    # Feature selection untuk clustering
    clustering_features: List[str] = field(default_factory=lambda: [
        "recency", "frequency", "monetary",
        "avg_transaction_value", "purchase_consistency"
    ])
    
    # Cluster labels (akan di-assign berdasarkan karakteristik)
    cluster_labels: Dict[int, str] = field(default_factory=lambda: {
        0: "High Value",
        1: "Medium Value", 
        2: "Low Value"
    })


@dataclass
class ChurnConfig:
    """Konfigurasi untuk Churn Prediction"""
    
    # Model selection
    model_type: str = "random_forest"  # random_forest, xgboost, logistic
    
    # Train/test split
    test_size: float = 0.2
    random_state: int = 42
    
    # Random Forest parameters
    rf_n_estimators: int = 100
    rf_max_depth: Optional[int] = 10
    rf_min_samples_split: int = 5
    rf_min_samples_leaf: int = 2
    
    # XGBoost parameters
    xgb_n_estimators: int = 100
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.1
    xgb_subsample: float = 0.8
    
    # Logistic Regression parameters
    lr_max_iter: int = 1000
    lr_C: float = 1.0
    
    # Churn definition threshold (days since last purchase)
    churn_threshold_days: int = 90
    
    # Features untuk churn prediction
    churn_features: List[str] = field(default_factory=lambda: [
        "recency", "frequency", "monetary",
        "avg_days_between_purchases", "purchase_consistency",
        "days_since_first_purchase", "engagement_score",
        "spending_volatility", "transaction_count"
    ])
    
    # Class weight untuk imbalanced data
    use_class_weight: bool = True


@dataclass
class CLVConfig:
    """Konfigurasi untuk Customer Lifetime Value Prediction"""
    
    # Model selection
    model_type: str = "random_forest"  # linear, random_forest, gradient_boosting
    
    # Train/test split
    test_size: float = 0.2
    random_state: int = 42
    
    # Random Forest Regressor parameters
    rf_n_estimators: int = 100
    rf_max_depth: Optional[int] = 15
    
    # Gradient Boosting parameters
    gb_n_estimators: int = 100
    gb_max_depth: int = 5
    gb_learning_rate: float = 0.1
    
    # CLV calculation parameters
    prediction_period_months: int = 12  # Prediksi CLV untuk 12 bulan ke depan
    discount_rate: float = 0.1  # Annual discount rate
    
    # Features untuk CLV prediction
    clv_features: List[str] = field(default_factory=lambda: [
        "recency", "frequency", "monetary",
        "avg_transaction_value", "purchase_consistency",
        "customer_tenure_days", "purchase_velocity",
        "total_spending", "transaction_count"
    ])


@dataclass
class RFMModelConfig:
    """
    Master Configuration untuk RFM Modeling
    
    DATA LOCATION GUIDE:
    ====================
    Taruh file hasil Feature Engineering di SALAH SATU lokasi berikut:
    
    REKOMENDASI (Default):
        scripts/project2_sales_analytics/output/features/csv/
        ├── rfm_features.csv
        ├── behavioral_features.csv
        ├── temporal_features.csv
        ├── customer_features.csv
        ├── sales_by_customer.csv
        └── sales_details.csv
    
    ATAU gunakan argument --input dengan ABSOLUTE PATH:
        python run_rfm_pipeline.py --input "D:/path/to/your/features/csv"
    """
    
    base_input_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT))
    base_output_path: str = field(default_factory=lambda: str(RFM_DIR / "output"))
    
    # Input files dari feature engineering
    input_files: Dict[str, str] = field(default_factory=lambda: {
        "rfm_features": "rfm_features.csv",
        "behavioral_features": "behavioral_features.csv",
        "temporal_features": "temporal_features.csv",
        "customer_features": "customer_features.csv",
        "sales_by_customer": "sales_by_customer.csv",
        "sales_details": "sales_details.csv"
    })
    
    # Column mappings sesuai dengan data feature engineering
    column_mapping: Dict[str, str] = field(default_factory=lambda: {
        "customer_id": "customer_id",
        "recency": "recency",
        "frequency": "frequency", 
        "monetary": "monetary",
        "rfm_segment": "rfm_segment",
        "value_tier": "value_tier",
        "churn_risk": "churn_risk",
        "avg_transaction_value": "avg_transaction_value",
        "purchase_consistency": "purchase_consistency",
        "engagement_score": "engagement_score",
        "customer_tenure_days": "customer_tenure_days",
        "transaction_count": "transaction_count",
        "total_spending": "total_spending"
    })
    
    # Sub-configurations
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    churn: ChurnConfig = field(default_factory=ChurnConfig)
    clv: CLVConfig = field(default_factory=CLVConfig)
    
    # Visualization settings
    figure_size: tuple = (12, 8)
    style: str = "whitegrid"
    palette: str = "husl"
    dpi: int = 100
    save_figures: bool = True
    
    # Export settings
    export_csv: bool = True
    export_pkl: bool = True
    export_json: bool = True
    
    # Logging
    verbose: bool = True
    
    def __post_init__(self):
        """Resolve paths after initialization."""
        self.base_input_path = self._resolve_path(self.base_input_path)
        self.base_output_path = self._resolve_path(self.base_output_path)
    
    def _resolve_path(self, path: str) -> str:
        """Convert relative path to absolute path based on project directory."""
        p = Path(path)
        if not p.is_absolute():
            p = PROJECT_DIR / p
        return str(p.resolve())
    
    def get_input_path(self, file_key: str) -> Path:
        """Get full path untuk input file"""
        filename = self.input_files.get(file_key, "")
        return Path(self.base_input_path) / filename
    
    def get_output_path(self, subdir: str = "") -> Path:
        """Get output path dengan optional subdirectory"""
        path = Path(self.base_output_path)
        if subdir:
            path = path / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def validate_input_files(self) -> Dict[str, bool]:
        """Check which input files exist."""
        status = {}
        for key, filename in self.input_files.items():
            path = Path(self.base_input_path) / filename
            status[key] = path.exists()
        return status
    
    def print_data_location_guide(self) -> None:
        """Print guide for where to place feature engineering data."""
        print("\n" + "=" * 70)
        print(" DATA LOCATION GUIDE")
        print("=" * 70)
        print(f"\nExpected feature engineering output directory:")
        print(f"  {self.base_input_path}")
        print(f"\nRequired files:")
        
        file_status = self.validate_input_files()
        for key, exists in file_status.items():
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {self.input_files[key]}")
        
        print(f"\nIf using different location, run with --input flag:")
        print(f'  python run_rfm_pipeline.py --input "D:/your/path/to/features/csv"')
        print("=" * 70 + "\n")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "base_input_path": self.base_input_path,
            "base_output_path": self.base_output_path,
            "input_files": self.input_files,
            "clustering": {
                "n_clusters": self.clustering.n_clusters,
                "algorithm": self.clustering.algorithm,
                "features": self.clustering.clustering_features
            },
            "churn": {
                "model_type": self.churn.model_type,
                "threshold_days": self.churn.churn_threshold_days,
                "features": self.churn.churn_features
            },
            "clv": {
                "model_type": self.clv.model_type,
                "prediction_months": self.clv.prediction_period_months,
                "features": self.clv.clv_features
            }
        }
    
    def save_config(self, filepath: str):
        """Save configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_json(cls, filepath: str) -> "RFMModelConfig":
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        config = cls()
        config.base_input_path = data.get("base_input_path", config.base_input_path)
        config.base_output_path = data.get("base_output_path", config.base_output_path)
        
        if "clustering" in data:
            config.clustering.n_clusters = data["clustering"].get("n_clusters", 3)
            config.clustering.algorithm = data["clustering"].get("algorithm", "kmeans")
        
        return config
