import pandas as pd
import numpy as np
from datetime import datetime
import os

# CONFIG
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'new_base_dataset_project1')
PO_FILE = os.path.join(DATA_DIR, '2_PO_Details.csv')
STOCK_FILE = os.path.join(DATA_DIR, '4_Current_Stock.csv')
DEFAULT_LEAD_TIME = 30

def enrich_logic():
    print("="*60)
    print("[*] ADVANCED LEAD TIME & STOCK PROJECTION")
    print("="*60)
    
    if not os.path.exists(PO_FILE) or not os.path.exists(STOCK_FILE):
        print("[X] Files not found!")
        return

    df_po = pd.read_csv(PO_FILE)
    df_po.columns = df_po.columns.str.strip()
    df_stock = pd.read_csv(STOCK_FILE)
    df_stock.columns = df_stock.columns.str.strip()
    
    print(f"   Loaded {len(df_po)} POs and {len(df_stock)} Stock items")
    
    # 1. Calculate PO Age and Remaining Lead Time
    # Logic: Remaining = 30 - (Today - PO Date)
    # Example: PO Date Jan 1, Today Jan 22. Age 21. Remaining 9.
    
    now = pd.Timestamp.now().normalize()
    if 'trans_date' in df_po.columns:
        # Robust Date Parsing (Handle various formats)
        df_po['trans_date'] = pd.to_datetime(df_po['trans_date'], dayfirst=False, errors='coerce')
        if df_po['trans_date'].isna().all():
             df_po['trans_date'] = pd.to_datetime(df_po['trans_date'], format='mixed', errors='coerce')
        
        # Calculate Age in Days
        df_po['po_age_days'] = (now - df_po['trans_date']).dt.days
        
        # Calculate Remaining Days (ETA)
        # Calculate Remaining Days (ETA)
        # Use real lead time if available from Step 2, else Default
        if 'lead_time_days' in df_po.columns:
            # fillna with default just in case
            dynamic_lt = pd.to_numeric(df_po['lead_time_days'], errors='coerce').fillna(DEFAULT_LEAD_TIME)
            df_po['remaining_lead_time'] = dynamic_lt - df_po['po_age_days']
        else:
            df_po['remaining_lead_time'] = DEFAULT_LEAD_TIME - df_po['po_age_days']
        
        # arrival_status: 'Arrived' (if remaining <= 0), 'Incoming' (if > 0)
        # This is a heuristic. Real system would check 'Closed' status.
        df_po['status_prediction'] = df_po['remaining_lead_time'].apply(
            lambda x: 'Incoming' if x > 0 else 'Arrived/Late'
        )
        
        print("   [OK] Calculated PO Age and ETA")
    else:
        print("[X] 'trans_date' missing in PO file")
        return

    # 2. Aggregating Incoming Stock
    # "lead time juga mengupdate stock barang, karena quantity - dan +"
    # We sum quantity of 'Incoming' POs per item
    
    incoming_df = df_po[df_po['status_prediction'] == 'Incoming']
    print(f"   [i] Found {len(incoming_df)} PO lines likely 'Incoming' (Age < 30 days)")
    
    incoming_stats = incoming_df.groupby('item_no').agg({
        'quantity': 'sum',
        'remaining_lead_time': 'mean' # Avg ETA for incoming
    }).reset_index()
    
    incoming_stats.rename(columns={
        'quantity': 'incoming_qty', 
        'remaining_lead_time': 'avg_incoming_eta_days'
    }, inplace=True)
    
    # 3. Merging into Current Stock
    # Current Stock + Incoming = Projected Stock
    
    # Ensure item_no matches type
    df_stock['item_no'] = df_stock['item_no'].astype(str)
    incoming_stats['item_no'] = incoming_stats['item_no'].astype(str)
    
    # Idempotency: Drop existing enriched/duplicate columns if re-running
    cols_to_drop = [c for c in df_stock.columns if c in ['incoming_qty', 'avg_incoming_eta_days'] or '_x' in c or '_y' in c]
    if cols_to_drop:
        # print(f"   [i] Dropping existing columns to prevent duplicates: {cols_to_drop}")
        df_stock.drop(columns=cols_to_drop, inplace=True)
    
    print(f"   [D] Stock Cols: {list(df_stock.columns)}")
    print(f"   [D] Incoming Cols: {list(incoming_stats.columns)}")
    
    df_stock_enriched = pd.merge(df_stock, incoming_stats, on='item_no', how='left')
    
    # Fill NaN safely
    if 'incoming_qty' in df_stock_enriched.columns:
        df_stock_enriched['incoming_qty'] = df_stock_enriched['incoming_qty'].fillna(0)
    else:
        df_stock_enriched['incoming_qty'] = 0

    if 'avg_incoming_eta_days' in df_stock_enriched.columns:
        df_stock_enriched['avg_incoming_eta_days'] = df_stock_enriched['avg_incoming_eta_days'].fillna(0)
    else:
        df_stock_enriched['avg_incoming_eta_days'] = 0
    
    # Calculate Projected
    df_stock_enriched['projected_stock'] = df_stock_enriched['on_stock'] + df_stock_enriched['incoming_qty']
    
    # 4. Save Updates
    df_po.to_csv(PO_FILE, index=False)
    df_stock_enriched.to_csv(STOCK_FILE, index=False)
    
    print(f"   [OK] Updates Saved:")
    print(f"      - {PO_FILE}: Added 'remaining_lead_time', 'status_prediction'")
    print(f"      - {STOCK_FILE}: Added 'incoming_qty', 'projected_stock'")
    
    # Show Sample
    print("\n[?] SAMPLE STOCK UPDATE:")
    print(df_stock_enriched[df_stock_enriched['incoming_qty'] > 0][['item_no', 'on_stock', 'incoming_qty', 'projected_stock', 'avg_incoming_eta_days']].head())

if __name__ == "__main__":
    enrich_logic()
