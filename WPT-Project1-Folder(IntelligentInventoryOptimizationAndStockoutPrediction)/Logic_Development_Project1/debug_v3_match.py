
import pandas as pd

try:
    sales = pd.read_csv('field_mapping_csv_output/1_Sales_Details.csv')
    master = pd.read_csv('field_mapping_csv_output/5_Master_Items.csv')
    
    print(f"Sales Rows: {len(sales)}")
    print(f"Master Rows: {len(master)}")
    
    sales_items = set(sales['item_no'].dropna().unique())
    master_items = set(master['no'].dropna().unique())
    
    print(f"Unique Sales Items: {len(sales_items)}")
    print(f"Unique Master Items: {len(master_items)}")
    
    common = sales_items.intersection(master_items)
    print(f"Common Items: {len(common)}")
    
    print("\nSample Sales Items:", list(sales_items)[:5])
    print("Sample Master Items:", list(master_items)[:5])
    
    if len(common) == 0:
        print("\nCRITICAL: NO MATCHES FOUND!")
        # Check for whitespace/case
        s1 = list(sales_items)[0]
        m1 = list(master_items)[0]
        print(f"Sales item repr: {repr(s1)}")
        print(f"Master item repr: {repr(m1)}")
        
except Exception as e:
    print(f"Error: {e}")
