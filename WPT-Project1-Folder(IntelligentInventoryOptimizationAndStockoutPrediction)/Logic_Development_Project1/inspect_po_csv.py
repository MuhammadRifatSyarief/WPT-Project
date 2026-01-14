import pandas as pd
import os

po_file = 'field_mapping_csv_output/2_PO_Details.csv'
if not os.path.exists(po_file):
    print(f"File not found: {po_file}")
    exit()

try:
    df = pd.read_csv(po_file)
    print("First 5 PO Numbers in CSV:")
    # Print repr to see hidden characters/spaces
    print([repr(x) for x in df['number'].head().tolist()])
    
    target = "P-204A/PO/1123"
    print(f"\nChecking for exact match with '{target}':")
    # Check if target is in the numbers column
    is_present = target in df['number'].astype(str).values
    print(f"Present exactly? {is_present}")

    print(f"\nSearching for '{target}' (loose check):")
    # Check for P-204A
    matches = df[df['number'].astype(str).str.contains("P-204A", na=False)]
    if not matches.empty:
        print("Found rows containing 'P-204A':")
        print(matches['number'].tolist())
        print("Corresponding Date:", matches['trans_date'].tolist())
    else:
        print("No rows contain 'P-204A'")
        
except Exception as e:
    print(f"Error: {e}")
