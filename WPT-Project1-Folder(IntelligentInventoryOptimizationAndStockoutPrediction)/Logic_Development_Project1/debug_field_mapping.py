"""
Debug Field Mapping - Discover Actual API Response Structure
=============================================================
This script inspects the raw API responses to find the correct field names
for the field mapping logic.

Run this script first to see what fields actually exist in the API responses.
"""

import requests, hashlib, hmac, base64, json, time
from datetime import datetime, timedelta
import pandas as pd
import pytz
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG
# ============================================================
API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
wib = pytz.timezone('Asia/Jakarta')

# ============================================================
# API CLASS
# ============================================================
class AccurateAPI:
    def __init__(self, token, secret):
        self.token, self.secret, self.host = token, secret, None
        
    def sign(self, ts):
        return base64.b64encode(hmac.new(self.secret.encode(), ts.encode(), hashlib.sha256).digest()).decode()
    
    def headers(self):
        ts = datetime.now(wib).strftime('%d/%m/%Y %H:%M:%S')
        return {
            'Authorization': f'Bearer {self.token}',
            'X-Api-Timestamp': ts,
            'X-Api-Signature': self.sign(ts),
            'Content-Type': 'application/json'
        }
    
    def init(self):
        r = requests.post('https://account.accurate.id/api/api-token.do', headers=self.headers())
        d = r.json()
        k = 'database' if 'database' in d.get('d',{}) else 'data usaha'
        if d.get('s'):
            self.host = d['d'][k]['host']
            print(f'✅ Connected: {self.host}')
            return True
        print(f'❌ Connection failed: {d}')
        return False
    
    def get(self, ep, p=None):
        if not self.host:
            return None
        try:
            r = requests.get(f'{self.host}/accurate{ep}', headers=self.headers(), params=p, timeout=30)
            return r.json()
        except Exception as e:
            print(f'   Error: {e}')
            return None
    
    def pages(self, ep, p=None, mx=5):
        """Get paginated results (limited pages for diagnostic)"""
        p = p or {}
        data = []
        pg = 1
        while pg <= mx:
            p['sp.page'] = pg
            p['sp.pageSize'] = 100
            r = self.get(ep, p)
            if not r or not r.get('s') or not r.get('d', []):
                break
            data.extend(r['d'])
            if pg >= r.get('sp', {}).get('pageCount', 1):
                break
            pg += 1
            time.sleep(0.5)
        return data


# ============================================================
# MAIN DIAGNOSTIC
# ============================================================
def main():
    end_date = datetime.now().strftime('%d/%m/%Y')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')
    
    print('='*70)
    print('🔍 FIELD MAPPING DIAGNOSTIC - API Response Structure Discovery')
    print('='*70)
    print(f'📅 Date range: {start_date} to {end_date}')
    print()
    
    # Connect
    client = AccurateAPI(API_TOKEN, SIGNATURE_SECRET)
    if not client.init():
        return
    
    print()
    
    # ============================================================
    # 1. ITEM MASTER - Check available fields
    # ============================================================
    print('='*70)
    print('📦 1. ITEM MASTER STRUCTURE')
    print('='*70)
    
    items = client.pages('/api/item/list.do', {}, 1)  # Just 1 page
    if items:
        print(f'   ✅ Got {len(items)} items')
        print(f'   📋 COLUMNS ({len(items[0].keys())}):')
        for k, v in sorted(items[0].items()):
            print(f'      • {k}: {type(v).__name__} = {repr(v)[:50]}')
    else:
        print('   ❌ No items returned')
    
    print()
    
    # ============================================================
    # 2. SALES INVOICE LIST - Check available fields
    # ============================================================
    print('='*70)
    print('💰 2. SALES INVOICE LIST STRUCTURE')
    print('='*70)
    
    invoices = client.pages('/api/sales-invoice/list.do', 
        {'filter.transDate.>=': start_date, 'filter.transDate.<=': end_date}, 1)
    
    if invoices:
        print(f'   ✅ Got {len(invoices)} invoices')
        print(f'   📋 COLUMNS ({len(invoices[0].keys())}):')
        for k, v in sorted(invoices[0].items()):
            print(f'      • {k}: {type(v).__name__} = {repr(v)[:50]}')
        
        # Now get DETAIL of first invoice
        print()
        print('   📄 CHECKING DETAIL RESPONSE...')
        detail = client.get('/api/sales-invoice/detail.do', {'id': invoices[0]['id']})
        
        if detail and detail.get('s'):
            d = detail['d']
            print(f'   📋 DETAIL TOP-LEVEL KEYS ({len(d.keys())}):')
            for k in sorted(d.keys()):
                v = d[k]
                if isinstance(v, list):
                    print(f'      • {k}: list[{len(v)}]')
                    # Show first item structure
                    if v:
                        print(f'         First item keys ({len(v[0].keys())}):')
                        for ik, iv in sorted(v[0].items()):
                            print(f'            → {ik}: {type(iv).__name__} = {repr(iv)[:40]}')
                elif isinstance(v, dict):
                    print(f'      • {k}: dict[{len(v)}]')
                else:
                    print(f'      • {k}: {type(v).__name__} = {repr(v)[:40]}')
        else:
            print('   ❌ Failed to get detail')
    else:
        print('   ❌ No invoices returned')
    
    print()
    
    # ============================================================
    # 3. PURCHASE ORDER LIST & DETAIL
    # ============================================================
    print('='*70)
    print('🛒 3. PURCHASE ORDER STRUCTURE')
    print('='*70)
    
    pos = client.pages('/api/purchase-order/list.do',
        {'filter.transDate.>=': start_date, 'filter.transDate.<=': end_date}, 1)
    
    if pos:
        print(f'   ✅ Got {len(pos)} purchase orders')
        print(f'   📋 LIST COLUMNS ({len(pos[0].keys())}):')
        for k, v in sorted(pos[0].items()):
            print(f'      • {k}: {type(v).__name__} = {repr(v)[:50]}')
        
        # Get detail
        print()
        print('   📄 CHECKING DETAIL RESPONSE...')
        detail = client.get('/api/purchase-order/detail.do', {'id': pos[0]['id']})
        
        if detail and detail.get('s'):
            d = detail['d']
            print(f'   📋 DETAIL TOP-LEVEL KEYS ({len(d.keys())}):')
            for k in sorted(d.keys()):
                v = d[k]
                if isinstance(v, list):
                    print(f'      • {k}: list[{len(v)}]')
                    if v:
                        print(f'         First item keys ({len(v[0].keys())}):')
                        for ik, iv in sorted(v[0].items()):
                            print(f'            → {ik}: {type(iv).__name__} = {repr(iv)[:40]}')
                elif isinstance(v, dict):
                    print(f'      • {k}: dict[{len(v)}]')
                else:
                    print(f'      • {k}: {type(v).__name__} = {repr(v)[:40]}')
        else:
            print('   ❌ Failed to get detail')
    else:
        print('   ❌ No purchase orders returned')
    
    print()
    
    # ============================================================
    # 4. STOCK - list-stock.do
    # ============================================================
    print('='*70)
    print('📊 4. CURRENT STOCK STRUCTURE')
    print('='*70)
    
    stocks = client.pages('/api/item/list-stock.do', {}, 1)
    if stocks:
        print(f'   ✅ Got {len(stocks)} stock records')
        print(f'   📋 COLUMNS ({len(stocks[0].keys())}):')
        for k, v in sorted(stocks[0].items()):
            print(f'      • {k}: {type(v).__name__} = {repr(v)[:50]}')
    else:
        print('   ❌ No stock records returned')
    
    print()
    
    # ============================================================
    # 5. STOCK MUTATION HISTORY
    # ============================================================
    print('='*70)
    print('🔄 5. STOCK MUTATION HISTORY STRUCTURE')
    print('='*70)
    
    # Get one item ID
    if items:
        item_id = items[0].get('id')
        print(f'   Testing with item ID: {item_id}')
        
        mutation = client.get('/api/item/stock-mutation-history.do',
            {'id': item_id, 'startDate': start_date, 'endDate': end_date})
        
        if mutation and mutation.get('s') and mutation.get('d'):
            records = mutation['d']
            print(f'   ✅ Got {len(records)} mutation records')
            if records:
                print(f'   📋 COLUMNS ({len(records[0].keys())}):')
                for k, v in sorted(records[0].items()):
                    print(f'      • {k}: {type(v).__name__} = {repr(v)[:50]}')
        else:
            print('   ⚠️ No mutations for this item, trying another...')
            # Try a few more items
            for item in items[1:5]:
                item_id = item.get('id')
                mutation = client.get('/api/item/stock-mutation-history.do',
                    {'id': item_id, 'startDate': start_date, 'endDate': end_date})
                if mutation and mutation.get('s') and mutation.get('d'):
                    records = mutation['d']
                    print(f'   ✅ Got {len(records)} mutation records for item {item_id}')
                    if records:
                        print(f'   📋 COLUMNS ({len(records[0].keys())}):')
                        for k, v in sorted(records[0].items()):
                            print(f'      • {k}: {type(v).__name__} = {repr(v)[:50]}')
                    break
    
    print()
    print('='*70)
    print('🏁 DIAGNOSTIC COMPLETE')
    print('='*70)
    print()
    print('📝 NEXT STEPS:')
    print('   1. Review the field names above')
    print('   2. Compare with the field names used in field_mapping_logic_project1.ipynb')
    print('   3. Update the notebook to use the correct field names')
    print('   4. Especially check:')
    print('      - detailItem structure: does it have itemNo/itemName or just itemId?')
    print('      - list-stock.do: actual field for stock quantity')
    print('      - invoice list: actual field for customer name')


if __name__ == '__main__':
    main()
