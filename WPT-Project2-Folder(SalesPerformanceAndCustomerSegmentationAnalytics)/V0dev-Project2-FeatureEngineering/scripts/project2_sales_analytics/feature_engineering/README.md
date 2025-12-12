# Feature Engineering Module

## Overview

Modul ini berisi pipeline feature engineering untuk Sales Performance & Customer Segmentation Analytics.
Dibuat secara modular agar mudah di-maintain dan di-extend.

## Struktur Direktori

\`\`\`
feature_engineering/
│
├── __init__.py                      # Package initializer
├── README.md                        # Dokumentasi ini
│
├── config/
│   └── feature_config.py            # Konfigurasi feature engineering
│
├── customer_features/
│   ├── __init__.py
│   ├── rfm_features.py              # RFM-based features
│   ├── behavioral_features.py       # Customer behavior features
│   └── temporal_features.py         # Time-based customer features
│
├── product_features/
│   ├── __init__.py
│   ├── product_metrics.py           # Product performance metrics
│   └── basket_features.py           # Market basket derived features
│
├── transaction_features/
│   ├── __init__.py
│   ├── transaction_metrics.py       # Transaction-level features
│   └── aggregation_features.py      # Aggregated transaction features
│
├── pipeline/
│   ├── __init__.py
│   ├── feature_pipeline.py          # Main feature engineering pipeline
│   └── feature_validator.py         # Feature validation utilities
│
└── utils/
    ├── __init__.py
    └── feature_utils.py             # Helper functions
\`\`\`

## Penggunaan

### Basic Usage

\`\`\`python
from feature_engineering import FeatureEngineeringPipeline

# Initialize pipeline
pipeline = FeatureEngineeringPipeline(config_path="config/feature_config.py")

# Run full pipeline
features = pipeline.run(
    sales_details=sales_details_df,
    customers=customers_df,
    products=products_df
)

# Access individual feature sets
customer_features = features['customer']
product_features = features['product']
transaction_features = features['transaction']
\`\`\`

### Modular Usage

\`\`\`python
from feature_engineering.customer_features import RFMFeatureExtractor
from feature_engineering.product_features import ProductMetricsExtractor

# Use individual extractors
rfm_extractor = RFMFeatureExtractor()
rfm_features = rfm_extractor.extract(sales_by_customer_df)

product_extractor = ProductMetricsExtractor()
product_features = product_extractor.extract(sales_by_product_df)
\`\`\`

## Feature Categories

### 1. Customer Features (RFM Enhanced)

| Feature | Description | Type |
|---------|-------------|------|
| `recency_days` | Days since last purchase | Numeric |
| `frequency_count` | Total number of transactions | Numeric |
| `monetary_total` | Total spending amount | Numeric |
| `avg_order_value` | Average order value | Numeric |
| `purchase_consistency` | Std dev of purchase intervals | Numeric |
| `product_diversity` | Unique products purchased | Numeric |
| `category_preference` | Most purchased category | Categorical |

### 2. Product Features

| Feature | Description | Type |
|---------|-------------|------|
| `total_quantity_sold` | Units sold | Numeric |
| `total_revenue` | Revenue generated | Numeric |
| `unique_customers` | Customer reach | Numeric |
| `avg_basket_position` | Basket analysis metric | Numeric |
| `cross_sell_score` | Association strength | Numeric |

### 3. Transaction Features

| Feature | Description | Type |
|---------|-------------|------|
| `basket_size` | Items per transaction | Numeric |
| `basket_value` | Value per transaction | Numeric |
| `day_of_week` | Purchase day pattern | Categorical |
| `month` | Seasonal pattern | Categorical |
| `is_weekend` | Weekend purchase flag | Binary |

## Data Quality Requirements

Sebelum menjalankan feature engineering, pastikan:

- [x] `customer_id` 100% valid
- [x] `product_id` 100% valid  
- [x] `total_amount` > 0 (minimal 95%)
- [x] `trans_date` dalam format yang konsisten
- [x] Tidak ada duplicate transaction IDs

## Notes

- Module ini designed untuk handle missing values secara graceful
- Semua numeric features akan di-normalize jika diperlukan
- Categorical features akan di-encode sesuai kebutuhan model
