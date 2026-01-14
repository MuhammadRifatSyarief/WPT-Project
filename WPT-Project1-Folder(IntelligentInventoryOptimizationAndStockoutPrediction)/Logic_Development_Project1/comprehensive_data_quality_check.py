
import pandas as pd
import numpy as np
import os

OUTPUT_DIR = 'field_mapping_csv_output'

files = {
    'Sales': '1_Sales_Details.csv',
    'PO': '2_PO_Details.csv',
    'Mutations': '3_Stock_Mutations.csv',
    'Stock': '4_Current_Stock.csv',
    'Master': '5_Master_Items.csv'
}

def check_file(name, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        print(f"❌ {name}: File not found")
        return None
        
    df = pd.read_csv(path)
    rows = len(df)
    print(f"\n📊 ANALYSIS: {name.upper()}")
    print(f"   Rows: {rows:,}")
    
    # 1. Price/Cost Coverage Checking
    price_cols = [c for c in df.columns if 'price' in c.lower() or 'cost' in c.lower() or 'amount' in c.lower()]
    for c in price_cols:
        # FIX: Coerce to numeric
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        non_zero = df[df[c] > 0].shape[0]
        pct = (non_zero / rows * 100) if rows > 0 else 0
        print(f"   💰 {c} > 0: {non_zero:,} ({pct:.1f}%)")
        
    # 2. Null Checking
    nulls = df.isnull().sum()
    null_cols = nulls[nulls > 0]
    if not null_cols.empty:
        print("   ⚠️ Nulls found:")
        for c, v in null_cols.items():
            print(f"      - {c}: {v} nulls")
    else:
        print("   ✅ No Nulls detected")
        
    # 3. Specific Logic Checks
    if name == 'PO':
        # Check for potential Lead Time logic (Invoice Date vs PO Date if available?)
        # Current PO CSV might not have Invoice Date unless we added it.
        pass
        
    if name == 'Master':
        # Check price_source breakdown
        if 'price_source' in df.columns:
            print("   ℹ️ Price Source Breakdown:")
            print(df['price_source'].value_counts())

    return df

print("="*60)
print("🚀 COMPREHENSIVE DATA QUALITY AUDIT")
print("="*60)

dfs = {}
for name, fname in files.items():
    dfs[name] = check_file(name, fname)

# Cross-Check consistency
if dfs['Sales'] is not None and dfs['Master'] is not None:
    sales_items = set(dfs['Sales']['item_no'].dropna().unique())
    master_items = set(dfs['Master']['no'].dropna().unique())
    missing_in_master = sales_items - master_items
    print("\n🔗 RELATIONSHIP INTEGRITY")
    print(f"   Sales Items: {len(sales_items)}")
    print(f"   Master Items: {len(master_items)}")
    print(f"   Sales Items NOT in Master: {len(missing_in_master)}")
    if len(missing_in_master) > 0:
        print(f"   Examples missing: {list(missing_in_master)[:5]}")
