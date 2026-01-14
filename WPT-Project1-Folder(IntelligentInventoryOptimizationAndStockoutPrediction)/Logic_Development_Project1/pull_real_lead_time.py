import requests, hashlib, hmac, base64, time, os
import pandas as pd
from datetime import datetime, timedelta
import pytz
import argparse

# CONFIG ARGS
try:
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', help='Start Date dd/mm/yyyy')
    parser.add_argument('--end-date', help='End Date dd/mm/yyyy')
    args, _ = parser.parse_known_args()
    
    end_date = args.end_date if args.end_date else datetime.now().strftime('%d/%m/%Y')
    start_date = args.start_date if args.start_date else (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')
    print(f"   [i] Data Range: {start_date} to {end_date}")
except:
    end_date = datetime.now().strftime('%d/%m/%Y')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')

# CONFIG
API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
wib = pytz.timezone('Asia/Jakarta')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PO_FILE = os.path.join(BASE_DIR, 'data', 'new_base_dataset_project1', '2_PO_Details.csv')

class AccurateAPI:
    def __init__(self):
        self.req_count, self.last_req = 0, time.time()
        self.host = None
        self.init()
        
    def headers(self):
        ts = datetime.now(wib).strftime('%d/%m/%Y %H:%M:%S')
        sign = base64.b64encode(hmac.new(SIGNATURE_SECRET.encode(), ts.encode(), hashlib.sha256).digest()).decode()
        return {'Authorization': f'Bearer {API_TOKEN}', 'X-Api-Timestamp': ts, 'X-Api-Signature': sign, 'Content-Type': 'application/json'}
    
    def init(self):
        try:
            r = requests.post('https://account.accurate.id/api/api-token.do', headers=self.headers())
            d = r.json()
            if d.get('s'):
                self.host = d['d'][('database' if 'database' in d['d'] else 'data usaha')]['host']
                print(f"   [OK] Connected to API: {self.host}")
            else: print("   [X] API Auth Failed")
        except Exception as e: print(f"   [X] Connection Error: {e}")

    def get_pages(self, ep, p=None, mx=50):
        if not self.host: return []
        data, pg = [], 1
        while pg <= mx:
            p = p or {}; p['sp.page'] = pg; p['sp.pageSize'] = 100
            try:
                r = requests.get(f'{self.host}/accurate{ep}', headers=self.headers(), params=p).json()
                if not r.get('s') or not r.get('d'): break
                data.extend(r['d'])
                if pg >= r.get('sp',{}).get('pageCount',1): break
                pg += 1
            except: break
        return data

def main():
    print("="*60)
    print("[*] PULLING REAL LEAD TIME (RECEIVE ITEM HISTORY)")
    print("="*60)

    if not os.path.exists(PO_FILE): return
    df_po = pd.read_csv(PO_FILE)
    df_po.columns = df_po.columns.str.strip() # Remove potential whitespace
    if 'number' not in df_po.columns:
        print(f"   [X] Error: Column 'number' not found. Columns: {list(df_po.columns)}")
        return
    
    # 1. Map PO Number -> PO Date
    po_map = {}
    for _, row in df_po.iterrows():
        # normalize key
        k = str(row['number']).strip()
        po_map[k] = row['trans_date']
        
    print(f"   Target POs: {len(po_map)}")

    # 2. Fetch Receive Items
    # We fetch relevant fields. 'detailItem' usually contains linked source order.
    # To be safe, we might need to probe detail if list is insufficient.
    # List fields: id, number, transDate
    api = AccurateAPI()
    params = {
        'fields': 'id,number,transDate',
        'filter.transDate.>=': start_date,
        'filter.transDate.<=': end_date
    }
    receipts = api.get_pages('/api/receive-item/list.do', params, 200)
    print(f"   Found {len(receipts)} Receipts. Matching to POs...")
    
    matches = 0
    updates = {} # po_number -> lead_time_days
    
    # We scan receipts. For each receipt, we check if it links to our target POs.
    # Efficient: Only detail probe if needed?
    # Accurate Receipts usually link to PO via detail items.
    
    for i, r in enumerate(receipts):
        if (i+1) % 50 == 0: print(f"   Scanning Receipt {i+1} / {len(receipts)}...")
        
        # We MUST look at detail to find the source PO Number
        try:
            # Rate limit manual
            time.sleep(0.2)
            det = requests.get(f'{api.host}/accurate/api/receive-item/detail.do', headers=api.headers(), params={'id': r['id']}).json()
            if not det.get('s'): continue
            
            # The structure of detail usually has 'detailItem' list
            items = det['d'].get('detailItem', [])
            
            # Robust Extraction Logic based on Debug
            # Structure: item -> purchaseOrder -> number
            
            receipt_date = pd.to_datetime(r['transDate'], format='%d/%m/%Y', errors='coerce')
            
            for item in items:
                linked_po = None
                
                # Direct check
                if 'purchaseOrder' in item and isinstance(item['purchaseOrder'], dict):
                    linked_po = item['purchaseOrder'].get('number')
                
                # Check formatting (sometimes PO numbers have spaces/different formats)
                # We normalize both sides to be sure? 
                # For now, strict string match is usually okay if "P-2317/PO/1125" format is consistent.
                
                if linked_po:
                    # Normalize linked_po
                    linked_po_clean = str(linked_po).strip()

                    # Debug print for first few matches
                    if matches < 3:
                        print(f"   [DEBUG] Found Link: Receipt {r['transDate']} -> PO {linked_po_clean}")

                    if linked_po_clean in po_map:
                        po_date_str = po_map[linked_po_clean]
                        
                        # Handle potential missing date in CSV
                        if pd.isna(po_date_str) or str(po_date_str).lower() == 'nan' or str(po_date_str).strip() == '':
                             if matches < 3: print(f"   [!] Match found for {linked_po_clean} but trans_date is MISSING in CSV!")
                             continue

                        # Robust parsing
                        po_date = pd.to_datetime(po_date_str, format='%Y-%m-%d', errors='coerce') 
                        if pd.isna(po_date):
                             po_date = pd.to_datetime(po_date_str, format='%d/%m/%Y', errors='coerce')
                        
                        if pd.isna(po_date):
                             po_date = pd.to_datetime(po_date_str, errors='coerce') # Fallback

                        if pd.notnull(po_date) and pd.notnull(receipt_date):
                            lead_time = (receipt_date - po_date).days
                            if lead_time < 0: lead_time = 0
                            
                            updates[linked_po_clean] = lead_time
                            matches += 1
                            # Break inner loop
                            break 
                    else:
                         # Optional: debug why it didn't match (e.g. whitespace)
                         if matches < 3:
                             # Check if it exists loosely
                             loose_match = any(linked_po_clean in k for k in po_map.keys())
                             if loose_match:
                                 print(f"   [DEBUG] Strict match failed for '{linked_po_clean}', but partial match exists.") 
        except Exception as e: 
            # safe print
            pass

    print(f"   [OK] Matched {matches} Receipts to POs")
    
    # 3. Update CSV
    if updates:
        print("   [i] Updating CSV...")
        
        # Ensure column exists
        if 'lead_time_days' not in df_po.columns:
            df_po['lead_time_days'] = 30 # Default
            
        # Bulk Update using map for speed and safety
        # Converts updates dict to series mapping
        df_po['lead_time_days'] = df_po['number'].map(updates).fillna(df_po['lead_time_days'])
        
        # Mark which ones are real
        df_po['is_real_lead_time'] = df_po['number'].isin(updates.keys())
        
        df_po.to_csv(PO_FILE, index=False)
        print("   [OK] PO File Updated with REAL Lead Times")
        
        # Sample
        print(df_po[df_po['is_real_lead_time'] == True][['number', 'trans_date', 'lead_time_days']].head())
    else:
        print("   [!] No matching POs found in receipts. (Maybe different numbering format?)")

if __name__ == '__main__':
    main()
