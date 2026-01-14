import pandas as pd
import json

results = {}

# 1. Sales
try:
    df_sales = pd.read_csv('field_mapping_csv_output/1_Sales_Details.csv')
    results['sales_rows'] = len(df_sales)
    results['sales_price_coverage'] = (df_sales['unit_price'] > 0).mean() * 100
except:
    results['sales_error'] = True

# 2. PO
try:
    df_po = pd.read_csv('field_mapping_csv_output/2_PO_Details.csv')
    results['po_rows'] = len(df_po)
    results['po_price_coverage'] = (df_po['unit_price'] > 0).mean() * 100
except:
    results['po_error'] = True

# 3. Stock
try:
    df_stock = pd.read_csv('field_mapping_csv_output/4_Current_Stock.csv')
    results['stock_rows'] = len(df_stock)
    with_stock = df_stock[df_stock['on_stock'] > 0]
    results['stock_cost_coverage'] = (with_stock['avg_cost'] > 0).mean() * 100 if len(with_stock) > 0 else 0
    results['stock_price_coverage'] = (with_stock['unit_price'] > 0).mean() * 100 if len(with_stock) > 0 else 0
except:
    results['stock_error'] = True

# 4. Master
try:
    df_master = pd.read_csv('field_mapping_csv_output/5_Master_Items.csv')
    results['master_rows'] = len(df_master)
    results['master_price_coverage'] = (df_master['unitPrice'] > 0).mean() * 100
    results['master_cost_coverage'] = (df_master['avgCost'] > 0).mean() * 100
except:
    results['master_error'] = True

with open('final_metrics.json', 'w') as f:
    json.dump(results, f, indent=2)
