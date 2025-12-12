"""
Feature Engineering Configuration

Konfigurasi untuk semua parameter feature engineering.
Edit file ini untuk menyesuaikan threshold dan parameter.

Author: v0
Version: 1.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class RFMConfig:
    """Configuration for RFM feature extraction."""
    
    # Scoring quantiles (5 bins = quintiles)
    n_quantiles: int = 5
    
    # Recency scoring (lower is better, so reversed)
    recency_labels: List[int] = field(default_factory=lambda: [5, 4, 3, 2, 1])
    
    # Frequency scoring (higher is better)
    frequency_labels: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    
    # Monetary scoring (higher is better)
    monetary_labels: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    
    # Segment definitions based on RFM scores
    segment_rules: Dict[str, Dict] = field(default_factory=lambda: {
        "Champions": {"r_min": 4, "f_min": 4, "m_min": 4},
        "Loyal Customers": {"r_min": 3, "f_min": 3, "m_min": 3},
        "Potential Loyalist": {"r_min": 4, "f_min": 2, "m_min": 2},
        "Recent Customers": {"r_min": 4, "f_max": 2, "m_max": 2},
        "Promising": {"r_min": 3, "f_min": 1, "f_max": 2, "m_min": 1},
        "Need Attention": {"r_min": 2, "r_max": 3, "f_min": 2, "m_min": 2},
        "About To Sleep": {"r_min": 2, "r_max": 3, "f_max": 2, "m_max": 2},
        "At Risk": {"r_max": 2, "f_min": 3, "m_min": 3},
        "Cannot Lose Them": {"r_max": 2, "f_min": 4, "m_min": 4},
        "Hibernating": {"r_max": 2, "f_max": 2, "m_max": 2},
    })


@dataclass
class BehavioralConfig:
    """Configuration for behavioral feature extraction."""
    
    # Minimum transactions for consistency calculation
    min_transactions_for_consistency: int = 3
    
    # Outlier detection threshold (IQR multiplier)
    outlier_iqr_multiplier: float = 1.5
    
    # Product diversity thresholds
    low_diversity_threshold: int = 3
    high_diversity_threshold: int = 10


@dataclass
class TemporalConfig:
    """Configuration for temporal feature extraction."""
    
    # Analysis reference date (default: today)
    reference_date: Optional[datetime] = None
    
    # Weekend days (0=Monday, 6=Sunday)
    weekend_days: List[int] = field(default_factory=lambda: [5, 6])
    
    # Business hours definition
    business_hours_start: int = 9
    business_hours_end: int = 17
    
    # Seasonality bins
    seasons: Dict[str, List[int]] = field(default_factory=lambda: {
        "Q1": [1, 2, 3],
        "Q2": [4, 5, 6],
        "Q3": [7, 8, 9],
        "Q4": [10, 11, 12],
    })


@dataclass
class ProductConfig:
    """Configuration for product feature extraction."""
    
    # Minimum sales for product analysis
    min_sales_threshold: int = 5
    
    # Pareto threshold for top products
    pareto_threshold: float = 0.8
    
    # Product velocity categories
    velocity_bins: List[str] = field(default_factory=lambda: [
        "slow_moving", "moderate", "fast_moving", "top_seller"
    ])
    velocity_quantiles: List[float] = field(default_factory=lambda: [0.25, 0.5, 0.75, 1.0])


@dataclass  
class BasketConfig:
    """Configuration for market basket feature extraction."""
    
    # Minimum support for itemset
    min_support: float = 0.01
    
    # Minimum confidence for rules
    min_confidence: float = 0.5
    
    # Minimum lift for significant rules
    min_lift: float = 1.0
    
    # Maximum itemset size
    max_itemset_size: int = 3
    
    # Minimum transactions for analysis
    min_transactions: int = 100


@dataclass
class TransactionConfig:
    """Configuration for transaction feature extraction."""
    
    # Basket size thresholds
    small_basket_threshold: int = 2
    large_basket_threshold: int = 5
    
    # Value thresholds (in IDR)
    low_value_threshold: float = 500_000
    high_value_threshold: float = 5_000_000


@dataclass
class FeatureConfig:
    """
    Master configuration for all feature engineering.
    
    Usage:
        config = FeatureConfig()
        config.rfm.n_quantiles = 4  # Customize
    """
    
    rfm: RFMConfig = field(default_factory=RFMConfig)
    behavioral: BehavioralConfig = field(default_factory=BehavioralConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    product: ProductConfig = field(default_factory=ProductConfig)
    basket: BasketConfig = field(default_factory=BasketConfig)
    transaction: TransactionConfig = field(default_factory=TransactionConfig)
    
    # Output settings
    output_format: str = "parquet"  # parquet, csv, excel
    output_dir: str = "output/features"
    
    # Processing settings
    n_jobs: int = -1  # Parallel processing (-1 = all cores)
    verbose: bool = True
    random_state: int = 42
    
    def __post_init__(self):
        """Set default reference date if not provided."""
        if self.temporal.reference_date is None:
            self.temporal.reference_date = datetime.now()
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> "FeatureConfig":
        """Create config from dictionary."""
        return cls(
            rfm=RFMConfig(**config_dict.get("rfm", {})),
            behavioral=BehavioralConfig(**config_dict.get("behavioral", {})),
            temporal=TemporalConfig(**config_dict.get("temporal", {})),
            product=ProductConfig(**config_dict.get("product", {})),
            basket=BasketConfig(**config_dict.get("basket", {})),
            transaction=TransactionConfig(**config_dict.get("transaction", {})),
        )
    
    def to_dict(self) -> Dict:
        """Export config to dictionary."""
        from dataclasses import asdict
        return asdict(self)


# Default configuration instance
DEFAULT_CONFIG = FeatureConfig()
