# Step-by-Step Guide: Feature Engineering

Panduan lengkap untuk menjalankan feature engineering menggunakan data XLSX hasil data preparation.

## Prerequisites

\`\`\`bash
# Install dependencies
pip install pandas numpy openpyxl scikit-learn
\`\`\`

## Step 1: Persiapkan Data

### Option A: Menggunakan File XLSX (Recommended)

\`\`\`python
from data_loader import XLSXDataLoader, DataValidator

# 1. Load data dari XLSX
loader = XLSXDataLoader("sales_performance_analytics.xlsx")

# 2. Load semua sheets yang diperlukan untuk feature engineering
data = loader.load_for_feature_engineering()

# Output dictionary berisi:
# - sales_details: Detail transaksi (10,488 rows)
# - sales_by_customer: Agregasi per customer (814 rows)
# - sales_by_product: Agregasi per product (1,658 rows)
# - rfm_analysis: RFM scores (jika ada)
# - customers: Master customer (jika ada)
# - products: Master product (jika ada)
\`\`\`

### Option B: Menggunakan CSV Files

\`\`\`python
from data_loader import load_from_csv, convert_xlsx_to_csv

# Konversi XLSX ke CSV (satu kali)
convert_xlsx_to_csv(
    xlsx_path="sales_performance_analytics.xlsx",
    output_folder="./data/csv/",
)

# Load dari CSV
data = load_from_csv("./data/csv/")
\`\`\`

## Step 2: Validasi Data

\`\`\`python
# 3. Validasi data sebelum feature engineering
validator = DataValidator()
result = validator.validate_all(data)

if not result.is_valid:
    print("Data validation failed!")
    print(result)
    # Handle errors...
else:
    print("Data validation passed!")
\`\`\`

## Step 3: Extract RFM Features

\`\`\`python
from customer_features import RFMFeatureExtractor
from config import FeatureConfig

# 4. Setup configuration
config = FeatureConfig()

# 5. Extract RFM features
rfm_extractor = RFMFeatureExtractor(config.rfm)
rfm_features = rfm_extractor.extract(
    sales_details=data["sales_details"],
    reference_date="2025-12-31"  # Tanggal akhir periode analisis
)

print(f"RFM Features: {rfm_features.shape}")
print(rfm_features.head())
\`\`\`

## Step 4: Extract Behavioral Features

\`\`\`python
from customer_features import BehavioralFeatureExtractor

# 6. Extract behavioral features
behavioral_extractor = BehavioralFeatureExtractor(config.behavioral)
behavioral_features = behavioral_extractor.extract(
    sales_details=data["sales_details"],
    sales_by_customer=data["sales_by_customer"]
)

print(f"Behavioral Features: {behavioral_features.shape}")
\`\`\`

## Step 5: Extract Temporal Features

\`\`\`python
from customer_features import TemporalFeatureExtractor

# 7. Extract temporal features
temporal_extractor = TemporalFeatureExtractor(config.temporal)
temporal_features = temporal_extractor.extract(
    sales_details=data["sales_details"]
)

print(f"Temporal Features: {temporal_features.shape}")
\`\`\`

## Step 6: Combine All Features

\`\`\`python
import pandas as pd

# 8. Merge semua features
customer_features = rfm_features.merge(
    behavioral_features, on="customer_id", how="left"
).merge(
    temporal_features, on="customer_id", how="left"
)

print(f"Combined Features: {customer_features.shape}")
print(f"Columns: {customer_features.columns.tolist()}")
\`\`\`

## Step 7: Export Results

\`\`\`python
# 9. Export ke berbagai format

# Excel
customer_features.to_excel("customer_features.xlsx", index=False)

# CSV
customer_features.to_csv("customer_features.csv", index=False)

# Parquet (recommended untuk data besar)
customer_features.to_parquet("customer_features.parquet", index=False)
\`\`\`

## Quick Start (All-in-One)

\`\`\`python
"""
Quick Start Script - Copy and run this
"""
from data_loader import XLSXDataLoader, DataValidator
from customer_features import (
    RFMFeatureExtractor,
    BehavioralFeatureExtractor, 
    TemporalFeatureExtractor
)
from config import FeatureConfig

# === CONFIGURATION ===
XLSX_PATH = "sales_performance_analytics.xlsx"  # <-- EDIT PATH INI
REFERENCE_DATE = "2025-12-31"  # <-- Tanggal akhir analisis
OUTPUT_PATH = "customer_features_output.xlsx"

# === LOAD DATA ===
print("Loading data...")
loader = XLSXDataLoader(XLSX_PATH)
data = loader.load_for_feature_engineering()

# === VALIDATE ===
print("Validating...")
validator = DataValidator()
result = validator.validate_all(data)
if not result.is_valid:
    raise ValueError(f"Validation failed: {result.errors}")

# === EXTRACT FEATURES ===
print("Extracting features...")
config = FeatureConfig()

# RFM
rfm = RFMFeatureExtractor(config.rfm).extract(
    data["sales_details"], 
    reference_date=REFERENCE_DATE
)

# Behavioral
behavioral = BehavioralFeatureExtractor(config.behavioral).extract(
    data["sales_details"],
    data["sales_by_customer"]
)

# Temporal
temporal = TemporalFeatureExtractor(config.temporal).extract(
    data["sales_details"]
)

# === COMBINE ===
features = rfm.merge(behavioral, on="customer_id", how="left")
features = features.merge(temporal, on="customer_id", how="left")

# === EXPORT ===
features.to_excel(OUTPUT_PATH, index=False)
print(f"Done! Exported to {OUTPUT_PATH}")
print(f"Shape: {features.shape}")
\`\`\`

## Troubleshooting

### Error: "File tidak ditemukan"
\`\`\`python
# Pastikan path benar
import os
print(os.getcwd())  # Lihat current directory
print(os.listdir())  # Lihat file yang ada
\`\`\`

### Error: "Missing required columns"
\`\`\`python
# Cek kolom yang ada di data
print(data["sales_details"].columns.tolist())

# Cek mapping kolom
loader.get_summary()
\`\`\`

### Warning: "Date column is not datetime type"
\`\`\`python
# Convert manually
import pandas as pd
data["sales_details"]["trans_date"] = pd.to_datetime(
    data["sales_details"]["trans_date"],
    format="%Y-%m-%d"  # Sesuaikan format
)
\`\`\`

## File Structure

\`\`\`
feature_engineering/
├── config/
│   ├── __init__.py
│   └── feature_config.py     # Konfigurasi parameter
├── data_loader/
│   ├── __init__.py
│   ├── xlsx_loader.py        # Load XLSX/CSV
│   ├── data_validator.py     # Validasi data
│   └── data_schema.py        # Schema definition
├── customer_features/
│   ├── __init__.py
│   ├── rfm_features.py       # RFM extraction
│   ├── behavioral_features.py # Behavioral patterns
│   └── temporal_features.py   # Time-based features
├── utils/
│   ├── __init__.py
│   └── feature_utils.py      # Helper functions
├── README.md
└── STEP_BY_STEP_GUIDE.md     # <-- You are here
\`\`\`

## Next Steps

Setelah feature engineering selesai:

1. **Modeling** - Gunakan features untuk clustering (K-Means, DBSCAN)
2. **Visualization** - Buat dashboard untuk segment insights
3. **Action Plan** - Develop strategi per customer segment
