"""
Quick script to inspect CSV structure for Feature Engineering
"""
import pandas as pd
import os

BASE_PATH = r"D:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)\Logic_Development_Project1\field_mapping_csv_output"

files = [
    "1_Sales_Details.csv",
    "2_PO_Details.csv", 
    "3_Stock_Mutations.csv",
    "4_Current_Stock.csv",
    "5_Master_Items.csv"
]

output_lines = []

for f in files:
    filepath = os.path.join(BASE_PATH, f)
    output_lines.append(f"\n{'='*60}")
    output_lines.append(f"FILE: {f}")
    output_lines.append('='*60)
    
    df = pd.read_csv(filepath, nrows=5)
    output_lines.append(f"Columns ({len(df.columns)}):")
    for col in df.columns:
        output_lines.append(f"  - {col}")
    
    full_df = pd.read_csv(filepath)
    output_lines.append(f"\nShape: {len(full_df):,} rows")
    output_lines.append(f"\nSample data:")
    output_lines.append(df.head(2).to_string())

# Write to file
with open("csv_structure_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))
