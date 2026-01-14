"""
Feature Engineering Pipeline for Project 1: Intelligent Inventory Optimization
================================================================================

This pipeline transforms 5 base datasets into analytical feature sets for:
- Demand Forecasting
- Inventory Health Monitoring  
- Stockout Alerts
- Reorder Point Recommendations

Author: Generated for WPT Project 1
Date: 2025-12-24
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Pipeline configuration parameters"""
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    INPUT_DIR = Path(r'D:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)\data\new_base_dataset_project1')
    OUTPUT_DIR = Path(r'D:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)\data\new_base_dataset_project1')
    
    # Input files
    SALES_FILE = "1_Sales_Details.csv"
    PO_FILE = "2_PO_Details.csv"
    MUTATIONS_FILE = "3_Stock_Mutations.csv"
    CURRENT_STOCK_FILE = "4_Current_Stock.csv"
    MASTER_ITEMS_FILE = "5_Master_Items.csv"
    
    # Output files
    OUTPUT_AGGREGATED = "Master_Inventory_Feature_Set.csv"
    OUTPUT_PER_WAREHOUSE = "Master_Inventory_Feature_Set_PerWarehouse.csv"
    
    # Parameters
    Z_SCORE = 1.65  # 95% service level for safety stock
    ROLLING_WINDOWS = [7, 30]  # Days for rolling averages
    DEFAULT_LEAD_TIME = 14  # Default if no PO history
    
    # ABC Thresholds (cumulative revenue percentage)
    ABC_A_THRESHOLD = 0.80  # Top 80% revenue
    ABC_B_THRESHOLD = 0.95  # Next 15% revenue (80-95%)
    
    # XYZ Thresholds (Coefficient of Variation)
    XYZ_X_THRESHOLD = 0.5   # CV < 0.5 = Stable
    XYZ_Y_THRESHOLD = 1.0   # 0.5 <= CV < 1.0 = Variable


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def log_stage(stage_num: int, stage_name: str):
    """Print stage header"""
    print(f"\n{'='*60}")
    print(f"STAGE {stage_num}: {stage_name}")
    print(f"{'='*60}")


def log_info(message: str):
    """Print info message"""
    print(f"  [INFO] {message}")


def log_success(message: str):
    """Print success message"""
    print(f"  [OK] {message}")


def log_warning(message: str):
    """Print warning message"""
    print(f"  [!] {message}")


# =============================================================================
# STAGE 1: DATA LOADING & CLEANING
# =============================================================================

def stage1_load_and_clean() -> dict:
    """
    Load all 5 CSV files and perform initial cleaning.
    
    Returns:
        Dictionary containing all dataframes
    """
    log_stage(1, "DATA LOADING & CLEANING")
    
    dataframes = {}
    
    # Load Sales Details
    log_info(f"Loading {Config.SALES_FILE}...")
    sales_df = pd.read_csv(Config.INPUT_DIR / Config.SALES_FILE)
    sales_df['item_no'] = sales_df['item_no'].astype(str).str.strip()
    sales_df['trans_date'] = pd.to_datetime(sales_df['trans_date'], dayfirst=True, errors='coerce')
    sales_df['quantity'] = pd.to_numeric(sales_df['quantity'], errors='coerce').fillna(0)
    sales_df['total_price'] = pd.to_numeric(sales_df['total_price'], errors='coerce').fillna(0)
    sales_df['unit_price'] = pd.to_numeric(sales_df['unit_price'], errors='coerce').fillna(0)
    dataframes['sales'] = sales_df
    log_success(f"Sales: {len(sales_df):,} rows, {sales_df['item_no'].nunique():,} unique items")
    
    # Load PO Details
    log_info(f"Loading {Config.PO_FILE}...")
    po_df = pd.read_csv(Config.INPUT_DIR / Config.PO_FILE)
    po_df['item_no'] = po_df['item_no'].astype(str).str.strip()
    po_df['trans_date'] = pd.to_datetime(po_df['trans_date'], errors='coerce')
    if 'lead_time_days' in po_df.columns:
        po_df['lead_time_days'] = pd.to_numeric(po_df['lead_time_days'], errors='coerce').fillna(Config.DEFAULT_LEAD_TIME)
    else:
        po_df['lead_time_days'] = Config.DEFAULT_LEAD_TIME
    dataframes['po'] = po_df
    log_success(f"PO Details: {len(po_df):,} rows, {po_df['item_no'].nunique():,} unique items")
    
    # Load Stock Mutations
    log_info(f"Loading {Config.MUTATIONS_FILE}...")
    mutations_df = pd.read_csv(Config.INPUT_DIR / Config.MUTATIONS_FILE)
    mutations_df['item_no'] = mutations_df['item_no'].astype(str).str.strip()
    mutations_df['date'] = pd.to_datetime(mutations_df['date'], dayfirst=True, errors='coerce')
    mutations_df['qty_change'] = pd.to_numeric(mutations_df['qty_change'], errors='coerce').fillna(0)
    dataframes['mutations'] = mutations_df
    log_success(f"Mutations: {len(mutations_df):,} rows, {mutations_df['item_no'].nunique():,} unique items")
    
    # Load Current Stock
    log_info(f"Loading {Config.CURRENT_STOCK_FILE}...")
    current_stock_df = pd.read_csv(Config.INPUT_DIR / Config.CURRENT_STOCK_FILE)
    current_stock_df['item_no'] = current_stock_df['item_no'].astype(str).str.strip()
    current_stock_df['on_stock'] = pd.to_numeric(current_stock_df['on_stock'], errors='coerce').fillna(0)
    current_stock_df['avg_cost'] = pd.to_numeric(current_stock_df['avg_cost'], errors='coerce').fillna(0)
    if 'incoming_qty' in current_stock_df.columns:
        current_stock_df['incoming_qty'] = pd.to_numeric(current_stock_df['incoming_qty'], errors='coerce').fillna(0)
    else:
        current_stock_df['incoming_qty'] = 0
    dataframes['current_stock'] = current_stock_df
    log_success(f"Current Stock: {len(current_stock_df):,} rows, {current_stock_df['item_no'].nunique():,} unique items")
    
    # Load Master Items
    log_info(f"Loading {Config.MASTER_ITEMS_FILE}...")
    master_items_df = pd.read_csv(Config.INPUT_DIR / Config.MASTER_ITEMS_FILE)
    # Use 'no' column as item_no
    if 'no' in master_items_df.columns:
        master_items_df['item_no'] = master_items_df['no'].astype(str).str.strip()
    master_items_df['unitPrice'] = pd.to_numeric(master_items_df.get('unitPrice', 0), errors='coerce').fillna(0)
    master_items_df['avgCost'] = pd.to_numeric(master_items_df.get('avgCost', 0), errors='coerce').fillna(0)
    dataframes['master_items'] = master_items_df
    log_success(f"Master Items: {len(master_items_df):,} rows")
    
    return dataframes


# =============================================================================
# STAGE 2: TIME-SERIES METRICS ENGINE
# =============================================================================

def stage2_timeseries_metrics(dataframes: dict) -> pd.DataFrame:
    """
    Calculate time-series based metrics from sales data.
    
    Returns:
        DataFrame with time-series metrics per item
    """
    log_stage(2, "TIME-SERIES METRICS ENGINE")
    
    sales_df = dataframes['sales'].copy()
    
    # Filter valid sales
    sales_df = sales_df[sales_df['trans_date'].notna()]
    log_info(f"Valid sales records: {len(sales_df):,}")
    
    # Get date range
    min_date = sales_df['trans_date'].min()
    max_date = sales_df['trans_date'].max()
    log_info(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    
    # Aggregate daily sales per item
    log_info("Aggregating daily sales per item...")
    daily_sales = sales_df.groupby(['item_no', 'trans_date']).agg({
        'quantity': 'sum',
        'total_price': 'sum'
    }).reset_index()
    
    # Create complete date range for each item
    log_info("Creating complete daily matrix with zero-filling...")
    
    # Use union of Sales and Stock items to ensure coverage
    stock_items = dataframes['current_stock']['item_no'].astype(str).unique()
    sales_items = daily_sales['item_no'].unique()
    all_items = np.unique(np.concatenate([sales_items, stock_items]))
    
    log_info(f"Total unique items (Sales + Stock): {len(all_items):,}")
    
    date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    
    # Create full index
    full_index = pd.MultiIndex.from_product(
        [all_items, date_range],
        names=['item_no', 'trans_date']
    )
    
    # Reindex to fill gaps with 0
    daily_sales_indexed = daily_sales.set_index(['item_no', 'trans_date'])
    daily_sales_full = daily_sales_indexed.reindex(full_index, fill_value=0).reset_index()
    
    log_success(f"Daily matrix: {len(daily_sales_full):,} records ({len(all_items):,} items x {len(date_range)} days)")
    
    # Calculate rolling metrics per item
    log_info("Calculating rolling averages and volatility...")
    
    metrics_list = []
    
    for item_no in all_items:
        item_data = daily_sales_full[daily_sales_full['item_no'] == item_no].sort_values('trans_date')
        qty_series = item_data['quantity']
        revenue_series = item_data['total_price']
        
        # Rolling averages
        avg_7d = qty_series.tail(7).mean() if len(qty_series) >= 7 else qty_series.mean()
        avg_30d = qty_series.tail(30).mean() if len(qty_series) >= 30 else qty_series.mean()
        
        # Volatility (standard deviation)
        sales_volatility = qty_series.std() if len(qty_series) > 1 else 0
        
        # Total revenue
        total_revenue = revenue_series.sum()
        
        # Total quantity sold
        total_qty_sold = qty_series.sum()
        
        # Average daily sales (last 30 days for recency)
        avg_daily_sales = avg_30d
        
        metrics_list.append({
            'item_no': item_no,
            'avg_sales_7d': round(avg_7d, 2),
            'avg_sales_30d': round(avg_30d, 2),
            'avg_daily_sales': round(avg_daily_sales, 2),
            'sales_volatility': round(sales_volatility, 2),
            'total_revenue': round(total_revenue, 2),
            'total_qty_sold': round(total_qty_sold, 2)
        })
    
    ts_metrics_df = pd.DataFrame(metrics_list)
    log_success(f"Time-series metrics calculated for {len(ts_metrics_df):,} items")
    
    return ts_metrics_df


# =============================================================================
# STAGE 3: ADVANCED PRODUCT PROFILING
# =============================================================================

def stage3_product_profiling(ts_metrics_df: pd.DataFrame, dataframes: dict) -> pd.DataFrame:
    """
    Calculate ABC, XYZ classification and lead time profiling.
    
    Returns:
        DataFrame with product profiles
    """
    log_stage(3, "ADVANCED PRODUCT PROFILING")
    
    profiles_df = ts_metrics_df.copy()
    
    # --- ABC Classification (Revenue-based) ---
    log_info("Calculating ABC classification (revenue-based)...")
    
    # Sort by revenue descending
    profiles_df = profiles_df.sort_values('total_revenue', ascending=False)
    
    # Calculate cumulative percentage
    total_revenue_sum = profiles_df['total_revenue'].sum()
    if total_revenue_sum > 0:
        profiles_df['revenue_cumsum'] = profiles_df['total_revenue'].cumsum()
        profiles_df['revenue_pct_cumsum'] = profiles_df['revenue_cumsum'] / total_revenue_sum
        
        # Assign ABC class
        def assign_abc(pct):
            if pct <= Config.ABC_A_THRESHOLD:
                return 'A'
            elif pct <= Config.ABC_B_THRESHOLD:
                return 'B'
            else:
                return 'C'
        
        profiles_df['abc_class'] = profiles_df['revenue_pct_cumsum'].apply(assign_abc)
    else:
        profiles_df['abc_class'] = 'C'
    
    # Count ABC distribution
    abc_counts = profiles_df['abc_class'].value_counts()
    log_success(f"ABC Distribution: A={abc_counts.get('A', 0)}, B={abc_counts.get('B', 0)}, C={abc_counts.get('C', 0)}")
    
    # --- XYZ Classification (Volatility-based) ---
    log_info("Calculating XYZ classification (volatility-based)...")
    
    # Calculate Coefficient of Variation (CV = StdDev / Mean)
    profiles_df['cv'] = np.where(
        profiles_df['avg_daily_sales'] > 0,
        profiles_df['sales_volatility'] / profiles_df['avg_daily_sales'],
        999  # High CV for items with no sales
    )
    
    def assign_xyz(cv):
        if cv < Config.XYZ_X_THRESHOLD:
            return 'X'
        elif cv < Config.XYZ_Y_THRESHOLD:
            return 'Y'
        else:
            return 'Z'
    
    profiles_df['xyz_class'] = profiles_df['cv'].apply(assign_xyz)
    
    # Count XYZ distribution
    xyz_counts = profiles_df['xyz_class'].value_counts()
    log_success(f"XYZ Distribution: X={xyz_counts.get('X', 0)}, Y={xyz_counts.get('Y', 0)}, Z={xyz_counts.get('Z', 0)}")
    
    # Combined ABC-XYZ class
    profiles_df['abc_xyz_class'] = profiles_df['abc_class'] + profiles_df['xyz_class']
    
    # --- Lead Time Profiling (from PO data) ---
    log_info("Calculating lead time statistics from PO data...")
    
    po_df = dataframes['po'].copy()
    
    lead_time_stats = po_df.groupby('item_no')['lead_time_days'].agg([
        ('avg_lead_time', 'mean'),
        ('max_lead_time', 'max'),
        ('lead_time_stddev', 'std')
    ]).reset_index()
    
    # Fill NaN stddev with 0 (items with single PO)
    lead_time_stats['lead_time_stddev'] = lead_time_stats['lead_time_stddev'].fillna(0)
    
    # Round values
    lead_time_stats['avg_lead_time'] = lead_time_stats['avg_lead_time'].round(1)
    lead_time_stats['max_lead_time'] = lead_time_stats['max_lead_time'].round(0)
    lead_time_stats['lead_time_stddev'] = lead_time_stats['lead_time_stddev'].round(1)
    
    log_success(f"Lead time stats calculated for {len(lead_time_stats):,} items")
    
    # Merge lead time into profiles
    profiles_df = profiles_df.merge(lead_time_stats, on='item_no', how='left')
    
    # Fill missing lead times with default
    profiles_df['avg_lead_time'] = profiles_df['avg_lead_time'].fillna(Config.DEFAULT_LEAD_TIME)
    profiles_df['max_lead_time'] = profiles_df['max_lead_time'].fillna(Config.DEFAULT_LEAD_TIME)
    profiles_df['lead_time_stddev'] = profiles_df['lead_time_stddev'].fillna(0)
    
    # Clean up temporary columns
    profiles_df = profiles_df.drop(columns=['revenue_cumsum', 'revenue_pct_cumsum', 'cv'], errors='ignore')
    
    return profiles_df


# =============================================================================
# STAGE 4: PREDICTIVE METRICS CALCULATION
# =============================================================================

def stage4_predictive_metrics(profiles_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Safety Stock, ROP, DIO, and Days Until Stockout.
    
    Returns:
        DataFrame with predictive metrics
    """
    log_stage(4, "PREDICTIVE METRICS CALCULATION")
    
    df = profiles_df.copy()
    
    # --- Safety Stock (Dynamic Formula) ---
    log_info(f"Calculating Safety Stock (Z-score = {Config.Z_SCORE})...")
    
    # Safety Stock = Z * σ_demand * √(Lead Time)
    # Where σ_demand = sales_volatility
    df['safety_stock'] = (
        Config.Z_SCORE * 
        df['sales_volatility'] * 
        np.sqrt(df['avg_lead_time'])
    ).round(0)
    
    # Minimum safety stock = 0
    df['safety_stock'] = df['safety_stock'].clip(lower=0)
    
    log_success(f"Safety Stock calculated. Range: {df['safety_stock'].min():.0f} - {df['safety_stock'].max():.0f}")
    
    # --- Reorder Point (ROP) ---
    log_info("Calculating Reorder Point (ROP)...")
    
    # ROP = (Avg Daily Sales × Avg Lead Time) + Safety Stock
    df['reorder_point'] = (
        (df['avg_daily_sales'] * df['avg_lead_time']) + df['safety_stock']
    ).round(0)
    
    # Minimum ROP = 0
    df['reorder_point'] = df['reorder_point'].clip(lower=0)
    
    log_success(f"ROP calculated. Range: {df['reorder_point'].min():.0f} - {df['reorder_point'].max():.0f}")
    
    return df


# =============================================================================
# STAGE 5: MASTER AGGREGATION & EXPORT
# =============================================================================

def stage5_aggregate_and_export(predictive_df: pd.DataFrame, dataframes: dict) -> tuple:
    """
    Merge all data and create final output files.
    
    Returns:
        Tuple of (aggregated_df, per_warehouse_df)
    """
    log_stage(5, "MASTER AGGREGATION & EXPORT")
    
    # --- Prepare Current Stock Data ---
    log_info("Preparing current stock data...")
    
    current_stock_df = dataframes['current_stock'].copy()
    master_items_df = dataframes['master_items'].copy()
    
    # === OUTPUT 1: AGGREGATED (Sum all warehouses) ===
    log_info("Creating AGGREGATED output (sum across warehouses)...")
    
    # Aggregate stock by item
    stock_aggregated = current_stock_df.groupby('item_no').agg({
        'on_stock': 'sum',
        'avg_cost': 'mean',
        'incoming_qty': 'sum'
    }).reset_index()
    
    stock_aggregated.columns = ['item_no', 'current_stock', 'avg_cost', 'incoming_qty']
    
    # Merge with predictive metrics
    master_aggregated = predictive_df.merge(stock_aggregated, on='item_no', how='left')
    
    # Merge with master items for names/categories
    master_items_subset = master_items_df[['item_no', 'name', 'itemType', 'category', 'unitPrice']].copy()
    master_items_subset.columns = ['item_no', 'item_name', 'item_type', 'category', 'unit_price']
    
    master_aggregated = master_aggregated.merge(master_items_subset, on='item_no', how='left')
    
    # Fill missing values
    master_aggregated['current_stock'] = master_aggregated['current_stock'].fillna(0)
    master_aggregated['incoming_qty'] = master_aggregated['incoming_qty'].fillna(0)
    master_aggregated['avg_cost'] = master_aggregated['avg_cost'].fillna(0)
    master_aggregated['item_name'] = master_aggregated['item_name'].fillna('Unknown')
    master_aggregated['category'] = master_aggregated['category'].fillna('Uncategorized')
    
    # --- Calculate Final Metrics (Need current stock) ---
    log_info("Calculating DIO and Days Until Stockout...")
    
    # DIO (Days Inventory Outstanding)
    master_aggregated['dio_days'] = np.where(
        master_aggregated['avg_daily_sales'] > 0,
        (master_aggregated['current_stock'] / master_aggregated['avg_daily_sales']).round(1),
        999  # No movement
    )
    
    # Days Until Stockout
    master_aggregated['days_until_stockout'] = np.where(
        master_aggregated['avg_daily_sales'] > 0,
        ((master_aggregated['current_stock'] + master_aggregated['incoming_qty']) / 
         master_aggregated['avg_daily_sales']).round(1),
        999  # No movement
    )
    
    # Needs Reorder flag
    master_aggregated['needs_reorder'] = (
        master_aggregated['current_stock'] <= master_aggregated['reorder_point']
    )
    
    # Stockout Risk Level
    def calc_stockout_risk(row):
        if row['days_until_stockout'] <= 7:
            return 'HIGH'
        elif row['days_until_stockout'] <= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    master_aggregated['stockout_risk'] = master_aggregated.apply(calc_stockout_risk, axis=1)
    
    # Reorder columns for better readability
    column_order = [
        # Identifiers
        'item_no', 'item_name', 'item_type', 'category',
        # Current State
        'current_stock', 'incoming_qty', 'avg_cost', 'unit_price',
        # Time-Series Metrics
        'avg_sales_7d', 'avg_sales_30d', 'avg_daily_sales', 'sales_volatility',
        'total_revenue', 'total_qty_sold',
        # Classifications
        'abc_class', 'xyz_class', 'abc_xyz_class',
        # Lead Time
        'avg_lead_time', 'max_lead_time', 'lead_time_stddev',
        # Predictive Metrics
        'safety_stock', 'reorder_point', 'dio_days', 'days_until_stockout',
        # Alerts
        'needs_reorder', 'stockout_risk'
    ]
    
    # Only include columns that exist
    final_columns = [c for c in column_order if c in master_aggregated.columns]
    master_aggregated = master_aggregated[final_columns]
    
    log_success(f"Aggregated output: {len(master_aggregated):,} items, {len(final_columns)} columns")
    
    # === OUTPUT 2: PER WAREHOUSE ===
    log_info("Creating PER-WAREHOUSE output...")
    
    # Keep original columns from current stock
    stock_per_warehouse = current_stock_df.copy()
    
    # Rename key columns for consistency (keep others as-is)
    column_rename = {
        'on_stock': 'current_stock'
    }
    stock_per_warehouse = stock_per_warehouse.rename(columns=column_rename)
    
    log_info(f"Current stock columns: {list(stock_per_warehouse.columns)}")
    
    # Merge with predictive metrics (item-level metrics apply to all warehouses)
    master_per_warehouse = stock_per_warehouse.merge(predictive_df, on='item_no', how='left')
    
    # Merge with master items
    master_per_warehouse = master_per_warehouse.merge(master_items_subset, on='item_no', how='left')
    
    # Fill missing values
    master_per_warehouse['current_stock'] = master_per_warehouse['current_stock'].fillna(0)
    if 'incoming_qty' in master_per_warehouse.columns:
        master_per_warehouse['incoming_qty'] = master_per_warehouse['incoming_qty'].fillna(0)
    else:
        master_per_warehouse['incoming_qty'] = 0
    
    # Calculate per-warehouse metrics
    master_per_warehouse['dio_days'] = np.where(
        master_per_warehouse['avg_daily_sales'] > 0,
        (master_per_warehouse['current_stock'] / master_per_warehouse['avg_daily_sales']).round(1),
        999
    )
    
    master_per_warehouse['days_until_stockout'] = np.where(
        master_per_warehouse['avg_daily_sales'] > 0,
        ((master_per_warehouse['current_stock'] + master_per_warehouse['incoming_qty']) / 
         master_per_warehouse['avg_daily_sales']).round(1),
        999
    )
    
    master_per_warehouse['needs_reorder'] = (
        master_per_warehouse['current_stock'] <= master_per_warehouse['reorder_point']
    )
    
    master_per_warehouse['stockout_risk'] = master_per_warehouse.apply(calc_stockout_risk, axis=1)
    
    log_success(f"Per-warehouse output: {len(master_per_warehouse):,} rows")
    
    # === EXPORT ===
    log_info("Exporting to CSV files...")
    
    output_path_agg = Config.OUTPUT_DIR / Config.OUTPUT_AGGREGATED
    output_path_wh = Config.OUTPUT_DIR / Config.OUTPUT_PER_WAREHOUSE
    
    master_aggregated.to_csv(output_path_agg, index=False, encoding='utf-8')
    master_per_warehouse.to_csv(output_path_wh, index=False, encoding='utf-8')
    
    log_success(f"Exported: {output_path_agg}")
    log_success(f"Exported: {output_path_wh}")
    
    return master_aggregated, master_per_warehouse


# =============================================================================
# VERIFICATION
# =============================================================================

def verify_output(master_aggregated: pd.DataFrame, master_per_warehouse: pd.DataFrame, dataframes: dict):
    """
    Perform verification checks on the output.
    """
    log_stage(6, "VERIFICATION")
    
    errors = []
    warnings = []
    
    # Check 1: Row count
    expected_items = dataframes['current_stock']['item_no'].nunique()
    actual_items = len(master_aggregated)
    if actual_items < expected_items * 0.9:  # Allow 10% tolerance
        warnings.append(f"Row count mismatch: Expected ~{expected_items}, Got {actual_items}")
    else:
        log_success(f"Row count OK: {actual_items} items (expected ~{expected_items})")
    
    # Check 2: Non-negative values
    negative_rop = (master_aggregated['reorder_point'] < 0).sum()
    negative_ss = (master_aggregated['safety_stock'] < 0).sum()
    if negative_rop > 0:
        errors.append(f"Found {negative_rop} negative ROP values")
    else:
        log_success(f"All ROP values non-negative")
    
    if negative_ss > 0:
        errors.append(f"Found {negative_ss} negative Safety Stock values")
    else:
        log_success(f"All Safety Stock values non-negative")
    
    # Check 3: Classification coverage
    null_abc = master_aggregated['abc_class'].isna().sum()
    null_xyz = master_aggregated['xyz_class'].isna().sum()
    if null_abc > 0 or null_xyz > 0:
        warnings.append(f"Unclassified items: ABC={null_abc}, XYZ={null_xyz}")
    else:
        log_success(f"All items classified (ABC/XYZ)")
    
    # Check 4: Critical nulls
    critical_cols = ['item_no', 'current_stock', 'reorder_point', 'safety_stock']
    for col in critical_cols:
        null_count = master_aggregated[col].isna().sum()
        if null_count > 0:
            errors.append(f"Critical column '{col}' has {null_count} null values")
    
    if not errors:
        log_success("No critical null values")
    
    # Check 5: ABC distribution sanity
    abc_dist = master_aggregated['abc_class'].value_counts(normalize=True)
    log_info(f"ABC Distribution: A={abc_dist.get('A', 0):.1%}, B={abc_dist.get('B', 0):.1%}, C={abc_dist.get('C', 0):.1%}")
    
    # Check 6: Stockout risk summary
    risk_dist = master_aggregated['stockout_risk'].value_counts()
    log_info(f"Stockout Risk: HIGH={risk_dist.get('HIGH', 0)}, MEDIUM={risk_dist.get('MEDIUM', 0)}, LOW={risk_dist.get('LOW', 0)}")
    
    # Check 7: Needs reorder summary
    needs_reorder_count = master_aggregated['needs_reorder'].sum()
    log_info(f"Items needing reorder: {needs_reorder_count} ({needs_reorder_count/len(master_aggregated):.1%})")
    
    # Print summary
    print(f"\n{'='*60}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*60}")
    
    if errors:
        print(f"\n[X] ERRORS ({len(errors)}):")
        for e in errors:
            print(f"   - {e}")
    
    if warnings:
        print(f"\n[!] WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    
    if not errors and not warnings:
        print("\n[OK] ALL CHECKS PASSED!")
    
    return len(errors) == 0


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main pipeline execution"""
    print("\n" + "="*60)
    print("FEATURE ENGINEERING PIPELINE")
    print("Project 1: Intelligent Inventory Optimization")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Stage 1: Load Data
        dataframes = stage1_load_and_clean()
        
        # Stage 2: Time-Series Metrics
        ts_metrics = stage2_timeseries_metrics(dataframes)
        
        # Stage 3: Product Profiling
        profiles = stage3_product_profiling(ts_metrics, dataframes)
        
        # Stage 4: Predictive Metrics
        predictive = stage4_predictive_metrics(profiles)
        
        # Stage 5: Aggregation & Export
        master_agg, master_wh = stage5_aggregate_and_export(predictive, dataframes)
        
        # Verification
        success = verify_output(master_agg, master_wh, dataframes)
        
        print(f"\n{'='*60}")
        print("PIPELINE COMPLETED")
        print(f"{'='*60}")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nOutput files:")
        print(f"  1. {Config.OUTPUT_DIR / Config.OUTPUT_AGGREGATED}")
        print(f"  2. {Config.OUTPUT_DIR / Config.OUTPUT_PER_WAREHOUSE}")
        
        return success
        
    except Exception as e:
        print(f"\n[X] PIPELINE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
