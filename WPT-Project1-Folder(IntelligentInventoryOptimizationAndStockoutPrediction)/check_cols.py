import pandas as pd
try:
    df = pd.read_csv(r"D:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)\data\processed\temp_preprocessed\Final_sales_details.csv", nrows=1)
    print(list(df.columns))
except Exception as e:
    print(e)
