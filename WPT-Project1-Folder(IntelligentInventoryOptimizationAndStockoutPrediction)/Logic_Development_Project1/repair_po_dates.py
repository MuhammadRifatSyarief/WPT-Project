import pandas as pd
import requests
import hashlib
import hmac
import base64
import time
from datetime import datetime, timedelta
import pytz
import os

# CONFIG
API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
PO_FILE = 'field_mapping_csv_output/2_PO_Details.csv'
wib = pytz.timezone('Asia/Jakarta')

class AccurateAPI:
    def __init__(self):
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
                print(f"✅ Connected to API: {self.host}")
            else: print("❌ API Auth Failed")
        except Exception as e: print(f"❌ Connection Error: {e}")

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
    print("🛠️ REPAIRING PO DATES (LIGHTWEIGHT PULL)")
    print("="*60)

    if not os.path.exists(PO_FILE):
        print(f"File {PO_FILE} not found!")
        return

    df = pd.read_csv(PO_FILE)
    print(f"   Loaded {len(df)} rows. Checking for missing dates...")
    
    # Check if trans_date is indeed missing/nan
    # We'll reload it cleanly
    
    start_date = (datetime.now() - timedelta(days=120)).strftime('%d/%m/%Y') # Look back 120 days to be safe
    
    api = AccurateAPI()
    
    # Only fetch header info: number, transDate (Fast!)
    print(f"   Fetching PO Headers from {start_date}...")
    pos = api.get_pages('/api/purchase-order/list.do', {
        'fields': 'number,transDate',
        'filter.transDate.>=': start_date
    }, 100)
    
    print(f"   ✅ Fetched {len(pos)} PO headers.")
    
    # Create Map
    po_date_map = {p['number'].strip(): p['transDate'] for p in pos}
    
    # Update DataFrame
    updated = 0
    for idx, row in df.iterrows():
        po_num = str(row['number']).strip()
        current_date = str(row['trans_date'])
        
        # If current date is missing or nan
        if pd.isna(row['trans_date']) or current_date.lower() == 'nan' or current_date.strip() == '':
            if po_num in po_date_map:
                df.at[idx, 'trans_date'] = po_date_map[po_num]
                updated += 1
                
    print(f"   ✅ Repaired {updated} missing dates!")
    
    if updated > 0:
        df.to_csv(PO_FILE, index=False)
        print("   💾 CSV Saved.")
    else:
        print("   ⚠️ No dates needed update (or POs not found in range).")

if __name__ == '__main__':
    main()
