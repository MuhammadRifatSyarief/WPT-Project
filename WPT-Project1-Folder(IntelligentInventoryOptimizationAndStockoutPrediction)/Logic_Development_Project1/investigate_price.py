import pandas as pd

# Investigate duplicate unitPrice issue
df_mi = pd.read_csv('field_mapping_csv_output/5_Master_Items.csv')

print('=== MASTER ITEMS UNITPRICE ANALYSIS ===')
print()

# Check for duplicates
price_counts = df_mi['unitPrice'].value_counts().head(20)
print('Top 20 most common unitPrice values:')
print(price_counts)
print()

# Check what's in the columns
print('Columns in Master Items:', list(df_mi.columns))
print()
print('Sample rows:')
print(df_mi.head(10).to_string())
print()

# Check items with same price
most_common_price = price_counts.index[0]
print(f'\nItems with unitPrice = {most_common_price}:')
same_price = df_mi[df_mi['unitPrice'] == most_common_price]
print(f'Count: {len(same_price)}')
print(same_price[['no', 'name', 'unitPrice']].head(10).to_string())

# Now check PO prices for these items
df_po = pd.read_csv('field_mapping_csv_output/2_PO_Details.csv')
print('\n=== PO PRICES FOR SAMPLE ITEMS ===')
sample_items = same_price['no'].head(5).tolist()
for item_no in sample_items:
    po_prices = df_po[df_po['item_no'] == item_no]['unit_price'].tolist()
    print(f'{item_no}: PO prices = {po_prices[:5]}')

# Check sales prices
df_sales = pd.read_csv('field_mapping_csv_output/1_Sales_Details.csv')
print('\n=== SALES PRICES FOR SAMPLE ITEMS ===')
for item_no in sample_items:
    sales_prices = df_sales[df_sales['item_no'] == item_no]['unit_price'].tolist()
    print(f'{item_no}: Sales prices = {sales_prices[:5]}')

# Write report
with open('unitprice_analysis.txt', 'w') as f:
    f.write('=== UNITPRICE DUPLICATION ANALYSIS ===\n\n')
    f.write(f'Total items: {len(df_mi)}\n')
    f.write(f'Unique unitPrice values: {df_mi["unitPrice"].nunique()}\n')
    f.write(f'Items with unitPrice = 0: {(df_mi["unitPrice"]==0).sum()}\n\n')
    f.write('Top 20 most common prices:\n')
    f.write(price_counts.to_string())
    
print('\nAnalysis saved to unitprice_analysis.txt')
