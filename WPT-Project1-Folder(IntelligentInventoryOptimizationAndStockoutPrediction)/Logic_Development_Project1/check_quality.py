import pandas as pd

output = []
output.append('=== DATA QUALITY REPORT ===')
output.append('')

# PO_Details
df_po = pd.read_csv('field_mapping_csv_output/2_PO_Details.csv')
output.append(f'2_PO_Details: {len(df_po)} rows')
output.append(f'  unit_price > 0: {(df_po["unit_price"]>0).sum()} ({(df_po["unit_price"]>0).sum()/len(df_po)*100:.1f}%)')
output.append(f'  total_price > 0: {(df_po["total_price"]>0).sum()} ({(df_po["total_price"]>0).sum()/len(df_po)*100:.1f}%)')
output.append('')

# Current_Stock
df_st = pd.read_csv('field_mapping_csv_output/4_Current_Stock.csv')
output.append(f'4_Current_Stock: {len(df_st)} rows')
with_stock = df_st[df_st['on_stock']>0]
output.append(f'  items with stock>0: {len(with_stock)}')
if len(with_stock) > 0:
    output.append(f'  avg_cost > 0 (where stock>0): {(with_stock["avg_cost"]>0).sum()} ({(with_stock["avg_cost"]>0).sum()/len(with_stock)*100:.1f}%)')
    output.append(f'  unit_price > 0 (where stock>0): {(with_stock["unit_price"]>0).sum()} ({(with_stock["unit_price"]>0).sum()/len(with_stock)*100:.1f}%)')
output.append('')

# Master_Items
df_mi = pd.read_csv('field_mapping_csv_output/5_Master_Items.csv')
output.append(f'5_Master_Items: {len(df_mi)} rows, columns: {list(df_mi.columns)}')
for col in df_mi.columns:
    if df_mi[col].dtype in ['int64', 'float64']:
        zeros = (df_mi[col] == 0).sum()
        output.append(f'  {col} > 0: {len(df_mi) - zeros} ({(len(df_mi) - zeros)/len(df_mi)*100:.1f}%)')
output.append('')

# Sales Details
df_s = pd.read_csv('field_mapping_csv_output/1_Sales_Details.csv')
output.append(f'1_Sales_Details: {len(df_s)} rows')
output.append(f'  unit_price > 0: {(df_s["unit_price"]>0).sum()} ({(df_s["unit_price"]>0).sum()/len(df_s)*100:.1f}%)')
output.append(f'  total_price > 0: {(df_s["total_price"]>0).sum()} ({(df_s["total_price"]>0).sum()/len(df_s)*100:.1f}%)')
if 'gross_profit' in df_s.columns:
    output.append(f'  gross_profit > 0: {(df_s["gross_profit"]>0).sum()} ({(df_s["gross_profit"]>0).sum()/len(df_s)*100:.1f}%)')
output.append('')

# Stock Mutations
df_m = pd.read_csv('field_mapping_csv_output/3_Stock_Mutations.csv')
output.append(f'3_Stock_Mutations: {len(df_m)} rows')
with_inc = df_m[df_m['increase']>0]
with_dec = df_m[df_m['decrease']>0]
if len(with_inc) > 0:
    output.append(f'  value_in > 0 (where increase>0): {(with_inc["value_in"]>0).sum()}/{len(with_inc)} ({(with_inc["value_in"]>0).sum()/len(with_inc)*100:.1f}%)')
if len(with_dec) > 0:
    output.append(f'  value_out > 0 (where decrease>0): {(with_dec["value_out"]>0).sum()}/{len(with_dec)} ({(with_dec["value_out"]>0).sum()/len(with_dec)*100:.1f}%)')
output.append('')

# Cross-check: PO item_no matching Master item_no
po_items = set(df_po['item_no'].dropna().unique())
mi_items = set(df_mi['no'].dropna().unique()) if 'no' in df_mi.columns else set()
matched = po_items.intersection(mi_items)
output.append(f'Cross-check PO item_no -> Master no:')
output.append(f'  PO unique items: {len(po_items)}')
output.append(f'  Master unique items: {len(mi_items)}')
if len(po_items) > 0:
    output.append(f'  Matched: {len(matched)} ({len(matched)/len(po_items)*100:.1f}% of PO items)')

# Write to file
with open('quality_report.txt', 'w') as f:
    f.write('\n'.join(output))
    
print('Report written to quality_report.txt')
