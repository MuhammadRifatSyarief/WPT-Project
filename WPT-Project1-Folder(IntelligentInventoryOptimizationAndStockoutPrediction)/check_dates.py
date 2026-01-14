import pandas as pd
import sys

def get_date_range(file_path, date_col):
    try:
        df = pd.read_csv(file_path, usecols=[date_col])
        df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        return f"{min_date} to {max_date} ({len(df)} rows)"
    except Exception as e:
        return str(e)

print("NEW Sales:", get_date_range(r"D:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)\data\new_base_dataset_project1\1_Sales_Details.csv", "trans_date"))
print("OLD Sales:", get_date_range(r"D:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)\data\processed\temp_preprocessed\Final_sales_details.csv", "transaction_date"))
