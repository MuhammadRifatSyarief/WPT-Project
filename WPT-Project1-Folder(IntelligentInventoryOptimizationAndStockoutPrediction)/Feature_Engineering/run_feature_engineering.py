"""
Self-contained Feature Engineering Pipeline with file logging
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
import sys

warnings.filterwarnings('ignore')

# Output log file
LOG_FILE = Path(__file__).parent / "pipeline_execution.log"

def log(msg):
    """Write to both console and log file"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

# Clear log file
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== Pipeline Started: {datetime.now()} ===\n\n")

# Configuration
Z_SCORE = 1.65
DEFAULT_LEAD_TIME = 14
ABC_A_THRESHOLD = 0.80
ABC_B_THRESHOLD = 0.95
XYZ_X_THRESHOLD = 0.5
XYZ_Y_THRESHOLD = 1.0

BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "Logic_Development_Project1" / "field_mapping_csv_output"
OUTPUT_DIR = Path(__file__).parent

log(f"BASE_DIR: {BASE_DIR}")
log(f"INPUT_DIR: {INPUT_DIR}")
log(f"OUTPUT_DIR: {OUTPUT_DIR}")

try:
    # =========================================================================
    # STAGE 1: DATA LOADING
    # =========================================================================
    log("\n" + "="*50)
    log("STAGE 1: DATA LOADING")
    log("="*50)
    
    # Load Sales
    log("Loading 1_Sales_Details.csv...")
    sales_df = pd.read_csv(INPUT_DIR / "1_Sales_Details.csv")
    sales_df['item_no'] = sales_df['item_no'].astype(str).str.strip()
    sales_df['trans_date'] = pd.to_datetime(sales_df['trans_date'], dayfirst=True, errors='coerce')
    sales_df['quantity'] = pd.to_numeric(sales_df['quantity'], errors='coerce').fillna(0)
    sales_df['total_price'] = pd.to_numeric(sales_df['total_price'], errors='coerce').fillna(0)
    log(f"  -> {len(sales_df):,} rows, {sales_df['item_no'].nunique():,} unique items")
    
    # Load PO Details
    log("Loading 2_PO_Details.csv...")
    po_df = pd.read_csv(INPUT_DIR / "2_PO_Details.csv")
    po_df['item_no'] = po_df['item_no'].astype(str).str.strip()
    if 'lead_time_days' in po_df.columns:
        po_df['lead_time_days'] = pd.to_numeric(po_df['lead_time_days'], errors='coerce').fillna(DEFAULT_LEAD_TIME)
    else:
        po_df['lead_time_days'] = DEFAULT_LEAD_TIME
    log(f"  -> {len(po_df):,} rows")
    
    # Load Stock Mutations
    log("Loading 3_Stock_Mutations.csv...")
    mutations_df = pd.read_csv(INPUT_DIR / "3_Stock_Mutations.csv")
    mutations_df['item_no'] = mutations_df['item_no'].astype(str).str.strip()
    log(f"  -> {len(mutations_df):,} rows")
    
    # Load Current Stock
    log("Loading 4_Current_Stock.csv...")
    current_stock_df = pd.read_csv(INPUT_DIR / "4_Current_Stock.csv")
    current_stock_df['item_no'] = current_stock_df['item_no'].astype(str).str.strip()
    current_stock_df['on_stock'] = pd.to_numeric(current_stock_df['on_stock'], errors='coerce').fillna(0)
    current_stock_df['avg_cost'] = pd.to_numeric(current_stock_df['avg_cost'], errors='coerce').fillna(0)
    if 'incoming_qty' in current_stock_df.columns:
        current_stock_df['incoming_qty'] = pd.to_numeric(current_stock_df['incoming_qty'], errors='coerce').fillna(0)
    else:
        current_stock_df['incoming_qty'] = 0
    log(f"  -> {len(current_stock_df):,} rows, {current_stock_df['item_no'].nunique():,} unique items")
    log(f"  -> Columns: {list(current_stock_df.columns)}")
    
    # Load Master Items
    log("Loading 5_Master_Items.csv...")
    master_items_df = pd.read_csv(INPUT_DIR / "5_Master_Items.csv")
    if 'no' in master_items_df.columns:
        master_items_df['item_no'] = master_items_df['no'].astype(str).str.strip()
    log(f"  -> {len(master_items_df):,} rows")
    
    # =========================================================================
    # STAGE 2: TIME-SERIES METRICS
    # =========================================================================
    log("\n" + "="*50)
    log("STAGE 2: TIME-SERIES METRICS")
    log("="*50)
    
    # Filter valid sales
    sales_df = sales_df[sales_df['trans_date'].notna()]
    log(f"Valid sales: {len(sales_df):,}")
    
    # Aggregate daily sales
    log("Aggregating daily sales per item...")
    daily_agg = sales_df.groupby('item_no').agg({
        'quantity': ['sum', 'mean', 'std'],
        'total_price': 'sum'
    }).reset_index()
    daily_agg.columns = ['item_no', 'total_qty_sold', 'avg_daily_sales', 'sales_volatility', 'total_revenue']
    
    # Fill NaN volatility with 0
    daily_agg['sales_volatility'] = daily_agg['sales_volatility'].fillna(0)
    
    # Calculate 7-day and 30-day averages from recent data
    max_date = sales_df['trans_date'].max()
    
    # Last 7 days
    sales_7d = sales_df[sales_df['trans_date'] >= max_date - pd.Timedelta(days=7)]
    avg_7d = sales_7d.groupby('item_no')['quantity'].sum() / 7
    avg_7d = avg_7d.reset_index()
    avg_7d.columns = ['item_no', 'avg_sales_7d']
    
    # Last 30 days
    sales_30d = sales_df[sales_df['trans_date'] >= max_date - pd.Timedelta(days=30)]
    avg_30d = sales_30d.groupby('item_no')['quantity'].sum() / 30
    avg_30d = avg_30d.reset_index()
    avg_30d.columns = ['item_no', 'avg_sales_30d']
    
    # Merge
    ts_metrics = daily_agg.merge(avg_7d, on='item_no', how='left')
    ts_metrics = ts_metrics.merge(avg_30d, on='item_no', how='left')
    ts_metrics['avg_sales_7d'] = ts_metrics['avg_sales_7d'].fillna(0)
    ts_metrics['avg_sales_30d'] = ts_metrics['avg_sales_30d'].fillna(0)
    
    # Use 30d average as daily baseline
    ts_metrics['avg_daily_sales'] = ts_metrics['avg_sales_30d']
    
    log(f"Time-series metrics: {len(ts_metrics):,} items")
    
    # =========================================================================
    # STAGE 3: PRODUCT PROFILING
    # =========================================================================
    log("\n" + "="*50)
    log("STAGE 3: PRODUCT PROFILING")
    log("="*50)
    
    profiles = ts_metrics.copy()
    
    # ABC Classification
    log("Calculating ABC classification...")
    profiles = profiles.sort_values('total_revenue', ascending=False)
    total_revenue_sum = profiles['total_revenue'].sum()
    if total_revenue_sum > 0:
        profiles['revenue_cumsum'] = profiles['total_revenue'].cumsum()
        profiles['revenue_pct'] = profiles['revenue_cumsum'] / total_revenue_sum
        profiles['abc_class'] = profiles['revenue_pct'].apply(
            lambda x: 'A' if x <= ABC_A_THRESHOLD else ('B' if x <= ABC_B_THRESHOLD else 'C')
        )
    else:
        profiles['abc_class'] = 'C'
    
    abc_counts = profiles['abc_class'].value_counts()
    log(f"  ABC: A={abc_counts.get('A', 0)}, B={abc_counts.get('B', 0)}, C={abc_counts.get('C', 0)}")
    
    # XYZ Classification
    log("Calculating XYZ classification...")
    profiles['cv'] = np.where(
        profiles['avg_daily_sales'] > 0,
        profiles['sales_volatility'] / profiles['avg_daily_sales'],
        999
    )
    profiles['xyz_class'] = profiles['cv'].apply(
        lambda x: 'X' if x < XYZ_X_THRESHOLD else ('Y' if x < XYZ_Y_THRESHOLD else 'Z')
    )
    
    xyz_counts = profiles['xyz_class'].value_counts()
    log(f"  XYZ: X={xyz_counts.get('X', 0)}, Y={xyz_counts.get('Y', 0)}, Z={xyz_counts.get('Z', 0)}")
    
    profiles['abc_xyz_class'] = profiles['abc_class'] + profiles['xyz_class']
    
    # Lead Time Profiling
    log("Calculating lead time stats...")
    lead_time_stats = po_df.groupby('item_no')['lead_time_days'].agg(['mean', 'max', 'std']).reset_index()
    lead_time_stats.columns = ['item_no', 'avg_lead_time', 'max_lead_time', 'lead_time_stddev']
    lead_time_stats['lead_time_stddev'] = lead_time_stats['lead_time_stddev'].fillna(0)
    
    profiles = profiles.merge(lead_time_stats, on='item_no', how='left')
    profiles['avg_lead_time'] = profiles['avg_lead_time'].fillna(DEFAULT_LEAD_TIME)
    profiles['max_lead_time'] = profiles['max_lead_time'].fillna(DEFAULT_LEAD_TIME)
    profiles['lead_time_stddev'] = profiles['lead_time_stddev'].fillna(0)
    
    log(f"Profiles: {len(profiles):,} items")
    
    # =========================================================================
    # STAGE 4: PREDICTIVE METRICS
    # =========================================================================
    log("\n" + "="*50)
    log("STAGE 4: PREDICTIVE METRICS")
    log("="*50)
    
    # Safety Stock
    log(f"Calculating Safety Stock (Z={Z_SCORE})...")
    profiles['safety_stock'] = (
        Z_SCORE * profiles['sales_volatility'] * np.sqrt(profiles['avg_lead_time'])
    ).round(0).clip(lower=0)
    
    # ROP
    log("Calculating Reorder Point...")
    profiles['reorder_point'] = (
        profiles['avg_daily_sales'] * profiles['avg_lead_time'] + profiles['safety_stock']
    ).round(0).clip(lower=0)
    
    log(f"  Safety Stock range: {profiles['safety_stock'].min():.0f} - {profiles['safety_stock'].max():.0f}")
    log(f"  ROP range: {profiles['reorder_point'].min():.0f} - {profiles['reorder_point'].max():.0f}")
    
    # =========================================================================
    # STAGE 5: AGGREGATION & EXPORT
    # =========================================================================
    log("\n" + "="*50)
    log("STAGE 5: AGGREGATION & EXPORT")
    log("="*50)
    
    # === OUTPUT 1: AGGREGATED ===
    log("Creating aggregated output...")
    
    # Aggregate current stock by item
    stock_agg = current_stock_df.groupby('item_no').agg({
        'on_stock': 'sum',
        'avg_cost': 'mean',
        'incoming_qty': 'sum'
    }).reset_index()
    stock_agg.columns = ['item_no', 'current_stock', 'avg_cost', 'incoming_qty']
    
    # Merge
    master_agg = profiles.merge(stock_agg, on='item_no', how='left')
    
    # Master items info
    master_info = master_items_df[['item_no', 'name', 'itemType', 'category', 'unitPrice']].copy()
    master_info.columns = ['item_no', 'item_name', 'item_type', 'category', 'unit_price']
    master_agg = master_agg.merge(master_info, on='item_no', how='left')
    
    # Fill missing
    master_agg['current_stock'] = master_agg['current_stock'].fillna(0)
    master_agg['incoming_qty'] = master_agg['incoming_qty'].fillna(0)
    master_agg['item_name'] = master_agg['item_name'].fillna('Unknown')
    
    # DIO
    master_agg['dio_days'] = np.where(
        master_agg['avg_daily_sales'] > 0,
        (master_agg['current_stock'] / master_agg['avg_daily_sales']).round(1),
        999
    )
    
    # Days until stockout
    master_agg['days_until_stockout'] = np.where(
        master_agg['avg_daily_sales'] > 0,
        ((master_agg['current_stock'] + master_agg['incoming_qty']) / master_agg['avg_daily_sales']).round(1),
        999
    )
    
    # Needs reorder
    master_agg['needs_reorder'] = master_agg['current_stock'] <= master_agg['reorder_point']
    
    # Stockout risk
    def calc_risk(row):
        if row['days_until_stockout'] <= 7:
            return 'HIGH'
        elif row['days_until_stockout'] <= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
    master_agg['stockout_risk'] = master_agg.apply(calc_risk, axis=1)
    
    # Select columns
    final_cols = [
        'item_no', 'item_name', 'item_type', 'category',
        'current_stock', 'incoming_qty', 'avg_cost', 'unit_price',
        'avg_sales_7d', 'avg_sales_30d', 'avg_daily_sales', 'sales_volatility',
        'total_revenue', 'total_qty_sold',
        'abc_class', 'xyz_class', 'abc_xyz_class',
        'avg_lead_time', 'max_lead_time', 'lead_time_stddev',
        'safety_stock', 'reorder_point', 'dio_days', 'days_until_stockout',
        'needs_reorder', 'stockout_risk'
    ]
    master_agg = master_agg[[c for c in final_cols if c in master_agg.columns]]
    
    # Export
    output_agg = OUTPUT_DIR / "Master_Inventory_Feature_Set.csv"
    master_agg.to_csv(output_agg, index=False, encoding='utf-8')
    log(f"Exported aggregated: {output_agg}")
    log(f"  -> {len(master_agg):,} items, {len(master_agg.columns)} columns")
    
    # === OUTPUT 2: PER WAREHOUSE ===
    log("\nCreating per-warehouse output...")
    
    # Keep warehouse detail
    stock_wh = current_stock_df.copy()
    stock_wh_cols = ['item_no', 'warehouse']
    if 'on_stock' in stock_wh.columns:
        stock_wh_cols.append('on_stock')
    stock_wh = stock_wh[stock_wh_cols]
    stock_wh.columns = ['item_no', 'warehouse', 'current_stock'] if len(stock_wh_cols) == 3 else ['item_no', 'warehouse']
    
    # Merge with profiles
    master_wh = stock_wh.merge(profiles, on='item_no', how='left')
    master_wh = master_wh.merge(master_info, on='item_no', how='left')
    
    # Calculate per-warehouse metrics
    master_wh['current_stock'] = master_wh['current_stock'].fillna(0)
    master_wh['dio_days'] = np.where(
        master_wh['avg_daily_sales'] > 0,
        (master_wh['current_stock'] / master_wh['avg_daily_sales']).round(1),
        999
    )
    master_wh['days_until_stockout'] = np.where(
        master_wh['avg_daily_sales'] > 0,
        (master_wh['current_stock'] / master_wh['avg_daily_sales']).round(1),
        999
    )
    master_wh['needs_reorder'] = master_wh['current_stock'] <= master_wh['reorder_point']
    master_wh['stockout_risk'] = master_wh.apply(calc_risk, axis=1)
    
    # Export
    output_wh = OUTPUT_DIR / "Master_Inventory_Feature_Set_PerWarehouse.csv"
    master_wh.to_csv(output_wh, index=False, encoding='utf-8')
    log(f"Exported per-warehouse: {output_wh}")
    log(f"  -> {len(master_wh):,} rows")
    
    # =========================================================================
    # VERIFICATION
    # =========================================================================
    log("\n" + "="*50)
    log("VERIFICATION")
    log("="*50)
    
    log(f"Items in aggregated output: {len(master_agg):,}")
    log(f"Rows in per-warehouse output: {len(master_wh):,}")
    log(f"Negative ROP values: {(master_agg['reorder_point'] < 0).sum()}")
    log(f"Negative Safety Stock: {(master_agg['safety_stock'] < 0).sum()}")
    log(f"Items needing reorder: {master_agg['needs_reorder'].sum()}")
    log(f"HIGH stockout risk: {(master_agg['stockout_risk'] == 'HIGH').sum()}")
    log(f"MEDIUM stockout risk: {(master_agg['stockout_risk'] == 'MEDIUM').sum()}")
    log(f"LOW stockout risk: {(master_agg['stockout_risk'] == 'LOW').sum()}")
    
    log("\n" + "="*50)
    log("PIPELINE COMPLETED SUCCESSFULLY!")
    log("="*50)
    log(f"Finished at: {datetime.now()}")

except Exception as e:
    log(f"\n\nERROR: {str(e)}")
    import traceback
    log(traceback.format_exc())
    sys.exit(1)
