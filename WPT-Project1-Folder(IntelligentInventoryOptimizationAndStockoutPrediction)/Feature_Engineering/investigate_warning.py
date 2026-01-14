"""
Investigate missing items warning
"""
import pandas as pd
from pathlib import Path

INPUT_DIR = Path(r"D:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)\Logic_Development_Project1\field_mapping_csv_output")

sales_df = pd.read_csv(INPUT_DIR / "1_Sales_Details.csv")
stock_df = pd.read_csv(INPUT_DIR / "4_Current_Stock.csv")
master_df = pd.read_csv(INPUT_DIR / "5_Master_Items.csv")

# Standardize
sales_items = set(sales_df['item_no'].astype(str).str.strip())
stock_items = set(stock_df['item_no'].astype(str).str.strip())
if 'no' in master_df.columns:
    master_items = set(master_df['no'].astype(str).str.strip())
else:
    master_items = set()

# Analysis
missing_in_sales = stock_items - sales_items
missing_in_stock = sales_items - stock_items

with open("investigation_result.txt", "w") as f:
    f.write(f"Stock Items (Unique): {len(stock_items)}\n")
    f.write(f"Sales Items (Unique): {len(sales_items)}\n")
    f.write(f"Master Items (Unique): {len(master_items)}\n\n")
    
    f.write(f"Items in Stock but NO Sales (The missing 363?): {len(missing_in_sales)}\n")
    f.write(f"Examples: {list(missing_in_sales)[:10]}\n\n")
    
    f.write(f"Items in Sales but NO Stock: {len(missing_in_stock)}\n")
    f.write(f"Examples: {list(missing_in_stock)[:10]}\n")

print("Investigation complete. Read investigation_result.txt")
