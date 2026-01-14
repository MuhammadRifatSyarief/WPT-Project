"""
Debug script to check pipeline execution step by step
"""
import sys
import traceback

log_file = open("debug_log.txt", "w", encoding="utf-8")

def log(msg):
    print(msg)
    log_file.write(msg + "\n")
    log_file.flush()

try:
    log("=== Starting Debug ===")
    
    log("Step 1: Import pandas...")
    import pandas as pd
    log(f"  OK - pandas version: {pd.__version__}")
    
    log("Step 2: Import numpy...")
    import numpy as np
    log(f"  OK - numpy version: {np.__version__}")
    
    log("Step 3: Import pathlib...")
    from pathlib import Path
    log("  OK")
    
    log("Step 4: Define paths...")
    BASE_DIR = Path(__file__).parent.parent
    INPUT_DIR = BASE_DIR / "Logic_Development_Project1" / "field_mapping_csv_output"
    log(f"  BASE_DIR: {BASE_DIR}")
    log(f"  INPUT_DIR: {INPUT_DIR}")
    log(f"  INPUT_DIR exists: {INPUT_DIR.exists()}")
    
    log("Step 5: List input files...")
    if INPUT_DIR.exists():
        for f in INPUT_DIR.iterdir():
            log(f"  - {f.name} ({f.stat().st_size:,} bytes)")
    
    log("Step 6: Try loading sales CSV...")
    sales_file = INPUT_DIR / "1_Sales_Details.csv"
    log(f"  File exists: {sales_file.exists()}")
    if sales_file.exists():
        sales_df = pd.read_csv(sales_file, nrows=5)
        log(f"  Loaded {len(sales_df)} rows")
        log(f"  Columns: {list(sales_df.columns)}")
    
    log("Step 7: Try loading PO CSV...")
    po_file = INPUT_DIR / "2_PO_Details.csv"
    if po_file.exists():
        po_df = pd.read_csv(po_file, nrows=5)
        log(f"  Loaded {len(po_df)} rows")
        log(f"  Columns: {list(po_df.columns)}")
    
    log("Step 8: Try loading Current Stock CSV...")
    stock_file = INPUT_DIR / "4_Current_Stock.csv"
    if stock_file.exists():
        stock_df = pd.read_csv(stock_file, nrows=5)
        log(f"  Loaded {len(stock_df)} rows")
        log(f"  Columns: {list(stock_df.columns)}")
    
    log("Step 9: Try loading Master Items CSV...")
    master_file = INPUT_DIR / "5_Master_Items.csv"
    if master_file.exists():
        master_df = pd.read_csv(master_file, nrows=5)
        log(f"  Loaded {len(master_df)} rows")
        log(f"  Columns: {list(master_df.columns)}")
    
    log("\n=== All basic checks passed! ===")

except Exception as e:
    log(f"\nERROR: {str(e)}")
    log(traceback.format_exc())

finally:
    log_file.close()
