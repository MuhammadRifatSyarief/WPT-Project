"""
MBA Configuration Module
========================

Centralized configuration for Market Basket Analysis pipeline.
All parameters can be overridden via environment variables or config file.

Author: Project 2 - Sales Analytics
Version: 1.3.0 - Robust Error Handling
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path


# This ensures paths work regardless of where you run the script from
MBA_DIR = Path(__file__).parent.parent  # scripts/project2_sales_analytics/modeling/mba
MODELING_DIR = MBA_DIR.parent  # scripts/project2_sales_analytics/modeling
PROJECT_DIR = MODELING_DIR.parent  # scripts/project2_sales_analytics

DEFAULT_FEATURE_ENGINEERING_OUTPUT = PROJECT_DIR / "output" / "features" / "csv"


@dataclass
class MBAConfig:
    """
    Configuration class for Market Basket Analysis.
    
    DATA LOCATION GUIDE:
    ====================
    Taruh file hasil Feature Engineering di SALAH SATU lokasi berikut:
    
    REKOMENDASI (Default):
        scripts/project2_sales_analytics/output/features/csv/
        ├── sales_details.csv
        ├── sales_by_product.csv
        ├── rfm_features.csv
        └── ...
    
    ATAU gunakan argument --input dengan ABSOLUTE PATH:
        python run_mba_pipeline.py --input "D:/path/to/your/features/csv/sales_details.csv"
    """
    
    # ===========================================
    # INPUT/OUTPUT PATHS - Feature Engineering Output
    # ===========================================
    input_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "sales_details.csv"))
    output_dir: str = field(default_factory=lambda: str(MBA_DIR / "output"))
    feature_engineering_dir: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT))
    
    # These are now direct string attributes, not just methods
    sales_details_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "sales_details.csv"))
    sales_by_product_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "sales_by_product.csv"))
    rfm_features_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "rfm_features.csv"))
    behavioral_features_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "behavioral_features.csv"))
    customer_features_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "customer_features.csv"))
    temporal_features_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "temporal_features.csv"))
    sales_by_customer_path: str = field(default_factory=lambda: str(DEFAULT_FEATURE_ENGINEERING_OUTPUT / "sales_by_customer.csv"))
    
    # ===========================================
    # COLUMN MAPPINGS - Sesuai sales_details.csv
    # ===========================================
    # Transaction columns
    transaction_id_col: str = "invoice_id"
    invoice_number_col: str = "invoice_number"
    date_col: str = "transaction_date"
    
    # Customer columns
    customer_id_col: str = "customer_id"
    customer_name_col: str = "customer_name"
    customer_category_col: str = "customer_category"
    
    # Product columns
    product_id_col: str = "product_id"
    product_code_col: str = "product_code"
    product_name_col: str = "product_name"
    product_category_col: str = "product_category"
    
    # Transaction value columns
    quantity_col: str = "quantity"
    unit_price_col: str = "unit_price"
    amount_col: str = "total_amount"
    discount_col: str = "discount"
    
    # Location columns
    branch_id_col: str = "branch_id"
    branch_name_col: str = "branch_name"
    warehouse_id_col: str = "warehouse_id"
    warehouse_name_col: str = "warehouse_name"
    
    # Other columns
    salesman_col: str = "salesman_name"
    currency_col: str = "currency_code"
    unit_col: str = "unit"
    
    # ===========================================
    # RFM FEATURE COLUMNS - Sesuai rfm_features.csv
    # ===========================================
    rfm_segment_col: str = "rfm_segment"
    rfm_score_col: str = "rfm_score"
    value_tier_col: str = "value_tier"
    r_score_col: str = "r_score"
    f_score_col: str = "f_score"
    m_score_col: str = "m_score"
    
    # ===========================================
    # PRODUCT FEATURE COLUMNS - Sesuai sales_by_product.csv
    # ===========================================
    total_quantity_sold_col: str = "total_quantity_sold"
    total_revenue_col: str = "total_revenue"
    order_count_col: str = "order_count"
    unique_customers_col: str = "unique_customers"
    revenue_contribution_col: str = "revenue_contribution_pct"
    
    # ===========================================
    # APRIORI/FP-GROWTH PARAMETERS
    # ===========================================
    min_support: float = 0.01  # 1% minimum support
    min_confidence: float = 0.3  # 30% minimum confidence
    min_lift: float = 1.0  # Positive association
    max_length: int = 4  # Maximum itemset size
    
    # ===========================================
    # ALGORITHM SELECTION
    # ===========================================
    algorithm: str = "fpgrowth"  # 'apriori' or 'fpgrowth'
    use_colnames: bool = True  # Use product names in rules
    
    # ===========================================
    # FILTERING OPTIONS
    # ===========================================
    min_items_per_transaction: int = 2  # Minimum items per basket
    min_transactions_per_product: int = 5  # Minimum product frequency
    exclude_products: List[str] = field(default_factory=list)
    include_categories: Optional[List[str]] = None
    
    # RFM Segment filtering (untuk analisis per segment)
    filter_by_rfm_segment: bool = False
    target_rfm_segments: Optional[List[str]] = None  # e.g., ['Champions', 'Loyal']
    
    # Customer value tier filtering
    filter_by_value_tier: bool = False
    target_value_tiers: Optional[List[str]] = None  # e.g., ['High', 'Medium']
    
    # ===========================================
    # OUTPUT OPTIONS
    # ===========================================
    export_formats: List[str] = field(default_factory=lambda: ["csv", "pkl", "json"])
    top_rules_count: int = 100  # Top N rules to export
    generate_visualizations: bool = True
    
    # ===========================================
    # LOGGING
    # ===========================================
    verbose: bool = True
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Validate and create directories after initialization."""
        # Resolve all paths
        self.input_path = self._resolve_path(self.input_path)
        self.output_dir = self._resolve_path(self.output_dir)
        self.feature_engineering_dir = self._resolve_path(self.feature_engineering_dir)
        
        self.sales_details_path = self._resolve_path(self.sales_details_path)
        self.sales_by_product_path = self._resolve_path(self.sales_by_product_path)
        self.rfm_features_path = self._resolve_path(self.rfm_features_path)
        self.behavioral_features_path = self._resolve_path(self.behavioral_features_path)
        self.customer_features_path = self._resolve_path(self.customer_features_path)
        self.temporal_features_path = self._resolve_path(self.temporal_features_path)
        self.sales_by_customer_path = self._resolve_path(self.sales_by_customer_path)
        
        # Update paths based on feature_engineering_dir if it was changed
        self._sync_feature_paths()
        
        self._validate_parameters()
        self._create_directories()
    
    def _resolve_path(self, path: str) -> str:
        """Convert relative path to absolute path based on project directory."""
        p = Path(path)
        if not p.is_absolute():
            # Make relative path absolute from project directory
            p = PROJECT_DIR / p
        return str(p.resolve())
    
    def _sync_feature_paths(self) -> None:
        """Sync feature file paths with feature_engineering_dir."""
        fe_dir = Path(self.feature_engineering_dir)
        
        # Only update if the path doesn't already match
        if Path(self.sales_details_path).parent != fe_dir:
            self.sales_details_path = str(fe_dir / "sales_details.csv")
        if Path(self.sales_by_product_path).parent != fe_dir:
            self.sales_by_product_path = str(fe_dir / "sales_by_product.csv")
        if Path(self.rfm_features_path).parent != fe_dir:
            self.rfm_features_path = str(fe_dir / "rfm_features.csv")
        if Path(self.behavioral_features_path).parent != fe_dir:
            self.behavioral_features_path = str(fe_dir / "behavioral_features.csv")
        if Path(self.customer_features_path).parent != fe_dir:
            self.customer_features_path = str(fe_dir / "customer_features.csv")
        if Path(self.temporal_features_path).parent != fe_dir:
            self.temporal_features_path = str(fe_dir / "temporal_features.csv")
        if Path(self.sales_by_customer_path).parent != fe_dir:
            self.sales_by_customer_path = str(fe_dir / "sales_by_customer.csv")
    
    def _validate_parameters(self) -> None:
        """Validate configuration parameters."""
        # Validate support
        if not 0.0 < self.min_support <= 1.0:
            raise ValueError(f"min_support must be between 0 and 1, got {self.min_support}")
        
        # Validate confidence
        if not 0.0 < self.min_confidence <= 1.0:
            raise ValueError(f"min_confidence must be between 0 and 1, got {self.min_confidence}")
            
        # Validate lift
        if self.min_lift < 0:
            raise ValueError(f"min_lift must be positive, got {self.min_lift}")
            
        # Validate algorithm
        if self.algorithm.lower() not in ['apriori', 'fpgrowth']:
            raise ValueError(f"algorithm must be 'apriori' or 'fpgrowth', got {self.algorithm}")
            
        # Validate max_length
        if self.max_length < 2:
            raise ValueError(f"max_length must be at least 2, got {self.max_length}")
    
    def _create_directories(self) -> None:
        """Create output directories if they don't exist."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir, "csv").mkdir(exist_ok=True)
        Path(self.output_dir, "pkl").mkdir(exist_ok=True)
        Path(self.output_dir, "json").mkdir(exist_ok=True)
        Path(self.output_dir, "visualizations").mkdir(exist_ok=True)
    
    def get_feature_file(self, filename: str) -> Path:
        """Get absolute path to a feature engineering output file."""
        return Path(self.feature_engineering_dir) / filename
    
    def get_sales_details_path(self) -> Path:
        return Path(self.sales_details_path)
    
    def get_sales_by_product_path(self) -> Path:
        return Path(self.sales_by_product_path)
    
    def get_rfm_features_path(self) -> Path:
        return Path(self.rfm_features_path)
    
    def get_behavioral_features_path(self) -> Path:
        return Path(self.behavioral_features_path)
    
    def get_customer_features_path(self) -> Path:
        return Path(self.customer_features_path)
    
    def validate_input_files(self) -> Dict[str, bool]:
        """Check which input files exist."""
        return {
            "sales_details": Path(self.sales_details_path).exists(),
            "sales_by_product": Path(self.sales_by_product_path).exists(),
            "rfm_features": Path(self.rfm_features_path).exists(),
            "behavioral_features": Path(self.behavioral_features_path).exists(),
            "customer_features": Path(self.customer_features_path).exists(),
            "temporal_features": Path(self.temporal_features_path).exists(),
            "sales_by_customer": Path(self.sales_by_customer_path).exists(),
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'input_path': self.input_path,
            'output_dir': self.output_dir,
            'feature_engineering_dir': self.feature_engineering_dir,
            'transaction_id_col': self.transaction_id_col,
            'product_id_col': self.product_id_col,
            'product_name_col': self.product_name_col,
            'customer_id_col': self.customer_id_col,
            'min_support': self.min_support,
            'min_confidence': self.min_confidence,
            'min_lift': self.min_lift,
            'max_length': self.max_length,
            'algorithm': self.algorithm,
            'use_colnames': self.use_colnames,
            'min_items_per_transaction': self.min_items_per_transaction,
            'min_transactions_per_product': self.min_transactions_per_product,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MBAConfig':
        """Create config from dictionary."""
        return cls(**config_dict)
    
    def print_data_location_guide(self) -> None:
        """Print guide for where to place feature engineering data."""
        print("\n" + "=" * 70)
        print(" DATA LOCATION GUIDE")
        print("=" * 70)
        print(f"\nExpected feature engineering output directory:")
        print(f"  {self.feature_engineering_dir}")
        print(f"\nExpected input file:")
        print(f"  {self.input_path}")
        print(f"\nRequired files:")
        
        file_status = self.validate_input_files()
        for key, exists in file_status.items():
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {key}.csv")
        
        print(f"\nIf using different location, run with --input flag:")
        print(f'  python run_mba_pipeline.py --input "D:/your/path/to/sales_details.csv"')
        print("=" * 70 + "\n")
    
    def __repr__(self) -> str:
        return (
            f"MBAConfig(\n"
            f"  algorithm={self.algorithm},\n"
            f"  min_support={self.min_support},\n"
            f"  min_confidence={self.min_confidence},\n"
            f"  min_lift={self.min_lift},\n"
            f"  input_path={self.input_path}\n"
            f")"
        )
