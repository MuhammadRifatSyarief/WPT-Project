#!/usr/bin/env python
"""
Main Script: Feature Engineering Pipeline

Script utama untuk menjalankan feature engineering dari file XLSX.
Edit konfigurasi di bagian CONFIG di bawah.

Usage:
    cd scripts/project2_sales_analytics/feature_engineering
    python run_feature_engineering.py

Author: v0
Version: 1.4 - Added comprehensive error handling and None checks
"""

import os
import sys
from pathlib import Path
from datetime import datetime

_CURRENT_DIR = Path(__file__).resolve().parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))

import pandas as pd

# Import modules using absolute imports from current directory
from data_loader.xlsx_loader import XLSXDataLoader, convert_xlsx_to_csv
from data_loader.data_validator import DataValidator, detect_columns
from data_loader.output_exporter import FeatureExporter
from data_loader.data_schema import find_column, COLUMN_ALIASES

from customer_features.rfm_features import RFMFeatureExtractor
from customer_features.behavioral_features import BehavioralFeatureExtractor
from customer_features.temporal_features import TemporalFeatureExtractor

from config.feature_config import FeatureConfig


# ============================================================
# CONFIG - EDIT BAGIAN INI
# ============================================================

# Path ke file XLSX hasil data preparation
XLSX_PATH = "sales_performance_analytics.xlsx"

# Tanggal referensi untuk RFM (akhir periode analisis)
# Format: YYYY-MM-DD atau None untuk tanggal hari ini
REFERENCE_DATE = "2024-12-31"

# Output settings
OUTPUT_DIR = "output/features"
CSV_OUTPUT_DIR = "output/csv_data"

# Export formats
EXPORT_FORMATS = ["csv", "pkl"]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def auto_detect_date_column(df: pd.DataFrame) -> str:
    """Auto-detect date column name from dataframe."""
    if df is None:
        raise ValueError("DataFrame is None, cannot detect date column")
    
    possible_names = [
        "transaction_date", "trans_date", "invoice_date", 
        "date", "order_date", "sale_date"
    ]
    
    for name in possible_names:
        actual = find_column(df, name, COLUMN_ALIASES)
        if actual:
            return actual
    
    # Fallback: find any column with 'date' in name
    date_cols = [c for c in df.columns if "date" in c.lower()]
    if date_cols:
        return date_cols[0]
    
    raise ValueError("No date column found in sales_details!")


def auto_detect_amount_column(df: pd.DataFrame) -> str:
    """Auto-detect amount column name from dataframe."""
    if df is None:
        raise ValueError("DataFrame is None, cannot detect amount column")
    
    possible_names = [
        "total_amount", "amount", "total_revenue", 
        "revenue", "line_total", "sales_amount"
    ]
    
    for name in possible_names:
        actual = find_column(df, name, COLUMN_ALIASES)
        if actual:
            return actual
    
    raise ValueError("No amount column found in sales_details!")


def filter_none_dataframes(data: dict) -> dict:
    """Remove None values from dictionary for export."""
    return {k: v for k, v in data.items() if v is not None}


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    """Main feature engineering pipeline."""
    
    print("\n" + "="*70)
    print(" FEATURE ENGINEERING PIPELINE ")
    print("="*70)
    print(f"Input: {XLSX_PATH}")
    print(f"Reference Date: {REFERENCE_DATE}")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"CSV Raw Data: {CSV_OUTPUT_DIR}/")
    print("="*70 + "\n")
    
    # Create output directories
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    
    csv_output_path = Path(CSV_OUTPUT_DIR)
    csv_output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize config
    config = FeatureConfig()
    
    # ========================================
    # STEP 0: Convert XLSX to CSV (Raw Data)
    # ========================================
    print("\n[STEP 0] Converting XLSX to CSV files...")
    
    if not Path(XLSX_PATH).exists():
        print(f"[ERROR] File not found: {XLSX_PATH}")
        print("\nPastikan file XLSX berada di direktori yang sama,")
        print("atau edit XLSX_PATH di bagian CONFIG.")
        sys.exit(1)
    
    csv_files = convert_xlsx_to_csv(
        xlsx_path=XLSX_PATH,
        output_folder=csv_output_path,
        verbose=True
    )
    
    print(f"\n[OK] Raw data saved to: {csv_output_path}")
    
    # ========================================
    # STEP 1: Load Data
    # ========================================
    print("\n[STEP 1] Loading data from XLSX...")
    
    loader = XLSXDataLoader(XLSX_PATH, verbose=True)
    data = loader.load_for_feature_engineering()
    
    # Show summary
    print("\nData Summary:")
    summary = loader.get_summary()
    print(summary.to_string(index=False))
    
    # ========================================
    # STEP 2: Validate Data
    # ========================================
    print("\n[STEP 2] Validating data...")
    
    validator = DataValidator(verbose=True)
    validation_result = validator.validate_all(data)
    
    if not validation_result.is_valid:
        print("\n[WARNING] Data validation has errors, but continuing...")
        print(validation_result)
    
    # ========================================
    # STEP 2.5: Auto-detect Column Names
    # ========================================
    print("\n[STEP 2.5] Auto-detecting column names...")
    
    sales_df = data.get("sales_details")
    
    if sales_df is None:
        print("[FATAL ERROR] sales_details is None - cannot continue!")
        sys.exit(1)
    
    date_col = auto_detect_date_column(sales_df)
    amount_col = auto_detect_amount_column(sales_df)
    
    print(f"   Date column: {date_col}")
    print(f"   Amount column: {amount_col}")
    
    # Detect all columns
    detected = detect_columns(sales_df)
    print(f"   All detected columns: {detected}")
    
    # ========================================
    # STEP 3: Extract RFM Features
    # ========================================
    print("\n[STEP 3] Extracting RFM features...")
    
    rfm_extractor = RFMFeatureExtractor(config.rfm)
    
    rfm_features = rfm_extractor.extract(
        sales_details=sales_df,
        reference_date=REFERENCE_DATE,
        date_col=date_col,
        amount_col=amount_col,
    )
    
    print(f"   RFM features: {rfm_features.shape[0]} customers, {rfm_features.shape[1]} features")
    print(f"   Columns: {list(rfm_features.columns)[:8]}...")
    
    # ========================================
    # STEP 4: Extract Behavioral Features
    # ========================================
    print("\n[STEP 4] Extracting behavioral features...")
    
    behavioral_extractor = BehavioralFeatureExtractor(config.behavioral)
    
    behavioral_features = behavioral_extractor.extract(
        sales_details=sales_df,
        sales_by_customer=data.get("sales_by_customer"),  # Can be None
        date_col=date_col,
        amount_col=amount_col,
    )
    
    print(f"   Behavioral features: {behavioral_features.shape[0]} customers, {behavioral_features.shape[1]} features")
    
    # ========================================
    # STEP 5: Extract Temporal Features
    # ========================================
    print("\n[STEP 5] Extracting temporal features...")
    
    temporal_extractor = TemporalFeatureExtractor(config.temporal)
    
    temporal_features = temporal_extractor.extract(
        sales_details=sales_df,
        date_col=date_col,
    )
    
    print(f"   Temporal features: {temporal_features.shape[0]} customers, {temporal_features.shape[1]} features")
    
    # ========================================
    # STEP 6: Combine All Features
    # ========================================
    print("\n[STEP 6] Combining all features...")
    
    # Merge all customer features
    customer_features = rfm_features.merge(
        behavioral_features, 
        on="customer_id", 
        how="left",
        suffixes=("", "_behavioral")
    )
    
    customer_features = customer_features.merge(
        temporal_features,
        on="customer_id",
        how="left",
        suffixes=("", "_temporal")
    )
    
    # Remove duplicate columns that might have been created
    duplicate_cols = [col for col in customer_features.columns if col.endswith('_behavioral') or col.endswith('_temporal')]
    if duplicate_cols:
        customer_features = customer_features.drop(columns=duplicate_cols)
    
    print(f"   Combined: {customer_features.shape[0]} customers, {customer_features.shape[1]} features")
    
    # ========================================
    # STEP 7: Export Results (CSV + PKL)
    # ========================================
    print("\n[STEP 7] Exporting results...")
    
    # Initialize exporter
    exporter = FeatureExporter(
        output_dir=output_path,
        add_timestamp=False,
        verbose=True,
    )
    
    # Prepare all feature DataFrames
    feature_data = {
        "customer_features": customer_features,
        "rfm_features": rfm_features,
        "behavioral_features": behavioral_features,
        "temporal_features": temporal_features,
    }
    
    if data.get("sales_details") is not None:
        feature_data["sales_details"] = data["sales_details"]
    if data.get("sales_by_customer") is not None:
        feature_data["sales_by_customer"] = data["sales_by_customer"]
    if data.get("sales_by_product") is not None:
        feature_data["sales_by_product"] = data["sales_by_product"]
    
    # Export for Streamlit
    export_result = exporter.export_for_streamlit(
        feature_data=feature_data,
        metadata={
            "project": "Sales Performance Analytics",
            "reference_date": REFERENCE_DATE,
            "source_file": XLSX_PATH,
            "export_date": datetime.now().isoformat(),
            "total_customers": len(customer_features),
            "total_features": len(customer_features.columns),
            "detected_columns": {
                "date_col": date_col,
                "amount_col": amount_col,
            }
        }
    )
    
    # ========================================
    # STEP 8: Generate RFM Segment Summary
    # ========================================
    print("\n[STEP 8] Generating RFM segment summary...")
    
    segment_summary = rfm_extractor.get_segment_summary(rfm_features)
    exporter.to_csv(segment_summary, "rfm_segment_summary")
    
    print("\nRFM Segment Distribution:")
    print(segment_summary[["rfm_segment", "customer_count", "customer_pct", "revenue_pct"]].to_string(index=False))
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "="*70)
    print(" FEATURE ENGINEERING COMPLETE ")
    print("="*70)
    
    print(f"""
Summary:
  - Customers processed: {customer_features.shape[0]:,}
  - Total features: {customer_features.shape[1]}
  - RFM features: {rfm_features.shape[1]}
  - Behavioral features: {behavioral_features.shape[1]}
  - Temporal features: {temporal_features.shape[1]}
  
Output Files:
  - Raw CSV data: {csv_output_path}/
  - Feature CSV: {output_path}/csv/
  - Feature PKL: {output_path}/pkl/
  - Metadata: {output_path}/metadata.json

Streamlit Usage:
  ------------------------------------
  import joblib
  
  # Load all data at once
  data = joblib.load("{output_path}/pkl/streamlit_data.pkl")
  customer_features = data['data']['customer_features']
  rfm_features = data['data']['rfm_features']
  
  # Or load individual CSV:
  import pandas as pd
  df = pd.read_csv("{output_path}/csv/customer_features.csv")
  ------------------------------------

Next Steps:
  1. Review features in output files
  2. Proceed to modeling (clustering, classification)
  3. Create visualization dashboard with Streamlit
""")
    
    # Export summary
    export_summary = exporter.get_export_summary()
    print("\nExported Files:")
    print(export_summary.to_string(index=False))
    
    return customer_features, export_result


if __name__ == "__main__":
    try:
        features, exports = main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
