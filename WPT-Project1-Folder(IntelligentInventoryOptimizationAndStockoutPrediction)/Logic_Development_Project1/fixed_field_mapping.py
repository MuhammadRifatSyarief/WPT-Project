"""
TRANSACTION-FIRST FIELD MAPPING v3 - Robust Multi-Source Data Enrichment
========================================================================
Architecture Change:
1. Transaction-First: Prices are constructed from Sales/PO history, not just Master data.
2. Bulk Reporting: Uses stock mutation summary for global values.
3. Vendor Fallback: Uses vendor-price API for inactive items.
4. No Empty Probes: Skips item/detail.do which returns 0s.
"""

import requests, hashlib, hmac, base64, json, time, os
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
import pytz
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG
# ============================================================
API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
wib = pytz.timezone('Asia/Jakarta')
# CONFIG ARGUMENTS
import argparse
try:
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', help='Start Date dd/mm/yyyy')
    parser.add_argument('--end-date', help='End Date dd/mm/yyyy')
    # Use parse_known_args to avoid error if other flags are passed
    args, _ = parser.parse_known_args()
    
    end_date = args.end_date if args.end_date else datetime.now().strftime('%d/%m/%Y')
    start_date = args.start_date if args.start_date else (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')
    
    print(f"   📅 Data Range: {start_date} to {end_date}")
except:
    # Fallback if wrapping script fails parsing
    end_date = datetime.now().strftime('%d/%m/%Y')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')

# AGGRESSIVE LIMITS FOR ACCURACY (USER REQUEST: NO LIMIT)
LIMIT_PO = 100000          
LIMIT_SALES = 100000       
LIMIT_INVOICE = 100000      
LIMIT_MUTATIONS = 100000   

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def safe_float(val, default=0.0):
    try:
        if val is None or str(val).lower() in ['nan', 'none', '']: return default
        return float(val)
    except: return default

def safe_str(val, default=''):
    if val is None or str(val).lower() in ['nan', 'none', '']: return default
    return str(val).strip()

def normalize_date(date_str, output_format='%Y-%m-%d'):
    if not date_str or date_str in ['', 'None', 'nan']: return ''
    formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d']
    for fmt in formats:
        try: return datetime.strptime(date_str, fmt).strftime(output_format)
        except: continue
    return date_str

def normalize_price(price, precision=2):
    return round(safe_float(price), precision)

# ============================================================
# API CLASS
# ============================================================
class AccurateAPI:
    def __init__(self, token, secret):
        self.token, self.secret, self.host = token, secret, None
        self.req_count, self.last_req = 0, time.time()
        
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
    
    def rate_limit(self):
        if time.time() - self.last_req >= 1:
            self.req_count, self.last_req = 0, time.time()
        if self.req_count >= 3:
            time.sleep(max(1.2 - (time.time() - self.last_req), 0))
            self.req_count, self.last_req = 0, time.time()
        self.req_count += 1
    
    def init(self):
        r = requests.post('https://account.accurate.id/api/api-token.do', headers=self.headers())
        try:
            d = r.json()
            k = 'database' if 'database' in d.get('d',{}) else 'data usaha'
            if d.get('s'):
                self.host = d['d'][k]['host']
                print(f'   [OK] Connected: {self.host}')
                return True
        except: pass
        print(f'[X] Connection failed: {r.text}')
        return False
    
    def get(self, ep, p=None):
        if not self.host: return None
        for i in range(4):
            self.rate_limit()
            try:
                r = requests.get(f'{self.host}/accurate{ep}', headers=self.headers(), params=p, timeout=45)
                if r.status_code == 429:
                    time.sleep(2**i + 5)
                    continue
                return r.json()
            except: time.sleep(2**i)
        return None
    
    def pages(self, ep, p=None, mx=50):
        p = p or {}
        data = []
        pg = 1
        while pg <= mx:
            p['sp.page'] = pg
            p['sp.pageSize'] = 100
            r = self.get(ep, p)
            if not r or not r.get('s') or not r.get('d', []): break
            data.extend(r['d'])
            if pg >= r.get('sp', {}).get('pageCount', 1): break
            pg += 1
            time.sleep(0.5)
        return data

# ============================================================
# PRICE ENGINE (Central Intelligence)
# ============================================================
class PriceEngine:
    """Stores all pricing signals from all sources"""
    def __init__(self):
        # Raw Data
        self.sales_history = defaultdict(list)    # item_no -> [prices]
        self.po_history = defaultdict(list)       # item_no -> [prices]
        self.invoice_history = defaultdict(list)  # item_no -> [prices]
        self.vendor_prices = defaultdict(float)   # item_no -> price
        self.master_meta = {}                     # item_id -> dict
        self.id_map = {}                          # id -> item_no
        self.stock_vals = {}                      # item_no -> {qty, cost}
        
    def add_sales(self, item_no, price):
        if price > 0: self.sales_history[item_no].append(price)
            
    def add_po(self, item_no, price):
        if price > 0: self.po_history[item_no].append(price)
            
    def add_invoice(self, item_no, price):
        if price > 0: self.invoice_history[item_no].append(price)
            
    def add_vendor_price(self, item_no, price):
        if price > 0: self.vendor_prices[item_no] = price

    def get_market_price(self, item_no):
        """Construct selling price from history"""
        # 1. Sales History (Real)
        if self.sales_history[item_no]:
            return np.mean(self.sales_history[item_no])
            
        # 2. PO History + 30% Markup
        if self.po_history[item_no]:
            return np.mean(self.po_history[item_no]) * 1.3
            
        # 3. Vendor Price + 30% Markup
        if self.vendor_prices[item_no] > 0:
            return self.vendor_prices[item_no] * 1.3
            
        return 0.0

    def get_replacement_cost(self, item_no):
        """Construct cost from history"""
        # 1. Invoice Cost (Realized)
        if self.invoice_history[item_no]:
            return np.mean(self.invoice_history[item_no])
            
        # 2. PO Cost (Estimated)
        if self.po_history[item_no]:
            return np.mean(self.po_history[item_no])
            
        # 3. Vendor Price
        if self.vendor_prices[item_no] > 0:
            return self.vendor_prices[item_no]
            
        return 0.0

# ============================================================
# MAIN PIPELINE
# ============================================================
def main():
    print('='*70)
    print('[*] TRANSACTION-FIRST DATA ENRICHMENT (v3 - PRODUCTION)')
    print('='*70)
    
    cl = AccurateAPI(API_TOKEN, SIGNATURE_SECRET)
    if not cl.init(): return
    
    pe = PriceEngine()
    
    # --------------------------------------------------------
    # 0. PHASE 0: BUILD ID MAP (Essential for Linkage)
    # --------------------------------------------------------
    print('\n[#] PHASE 0: BUILDING ITEM MAP')
    # We need to pull all items first to map ID -> No
    # This is fast as we only need 2 fields
    master_raw = cl.pages('/api/item/list.do', {'fields': 'id,no,name,itemType,itemCategoryName'}, 100)
    
    for m in master_raw:
        pe.id_map[m.get('id')] = safe_str(m.get('no'))
        # Initialize meta for later
        pe.master_meta[m.get('id')] = m
        
    print(f'   [OK] Mapped {len(master_raw)} items')

    # --------------------------------------------------------
    # 1. PULL VENDOR PRICES (The Baseline)
    # --------------------------------------------------------
    print('\n[1] PHASE 1: VENDOR PRICES')
    v_prices = cl.pages('/api/vendor-price/list.do', {'fields': 'itemId,itemNo,price,vendorId'}, 30)
    for v in v_prices:
        # Use itemNo directly as it is available here
        pe.add_vendor_price(safe_str(v.get('itemNo')), safe_float(v.get('price')))
    print(f'   [OK] Loaded {len(v_prices)} vendor prices')

    # --------------------------------------------------------
    # 2. PULL SALES HISTORY (High Volume)
    # --------------------------------------------------------
    print(f'\n[2] PHASE 2: SALES HISTORY (Limit {LIMIT_SALES})')
    invs = cl.pages('/api/sales-invoice/list.do', {
        'fields': 'id,number,transDate', 
        'filter.transDate.>=': start_date, 
        'filter.transDate.<=': end_date
    }, 100) # Get many pages
    
    process_invs = invs[:LIMIT_SALES]
    print(f'   Found {len(invs)} invoices, scanning {len(process_invs)}...')
    
    sales_recs = []
    
    for i, inv in enumerate(process_invs):
        if (i+1)%50==0: print(f'   Progress: {i+1}/{len(process_invs)}...')
        d = cl.get('/api/sales-invoice/detail.do', {'id': inv['id']})
        if not d or not d.get('s'): continue
        
        for it in (d['d'].get('detailItem') or []):
            # FIX: Use ID to populate No
            item_id = it.get('itemId')
            item_no = pe.id_map.get(item_id)
            
            # Fallback if not mapped yet (should be rare if master pulled first)
            if not item_no: item_no = safe_str(it.get('itemNo') or it.get('no'))
            
            qty = safe_float(it.get('quantity'))
            price = safe_float(it.get('unitPrice'))
            amt = safe_float(it.get('totalPrice'))
            
            # Recalc price if 0
            if price == 0 and qty > 0 and amt > 0: price = amt / qty
            
            if price > 0: pe.add_sales(item_no, price)
            
            cost = pe.get_replacement_cost(item_no)
            
            sales_recs.append({
                'trans_date': inv.get('transDate'),
                'number': inv.get('number'),
                'item_no': item_no,
                'item_name': normalize_item_name(it.get('item',{}).get('name') or it.get('itemName')),
                'quantity': qty,
                'unit_price': normalize_price(price),
                'total_price': normalize_price(amt),
                'estimated_cost': normalize_price(cost),
                'gross_profit': normalize_price(amt - (qty*cost)) if cost>0 else 0
            })
            
    print(f'   [OK] Extracted {len(sales_recs)} sales lines')

    # --------------------------------------------------------
    # 3. PULL PO HISTORY (High Volume)
    # --------------------------------------------------------
    print(f'\n[3] PHASE 3: PO HISTORY (Limit {LIMIT_PO})')
    pos = cl.pages('/api/purchase-order/list.do', {
        'fields': 'id,number,transDate,vendorName', 
        'filter.transDate.>=': start_date
    }, 100)
    
    process_pos = pos[:LIMIT_PO]
    print(f'   Found {len(pos)} POs, scanning {len(process_pos)}...')
    
    po_recs = []
    
    for i, po in enumerate(process_pos):
        if (i+1)%50==0: print(f'   Progress: {i+1}/{len(process_pos)}...')
        d = cl.get('/api/purchase-order/detail.do', {'id': po['id']})
        if not d or not d.get('s'): continue
        
        for it in (d['d'].get('detailItem') or []):
            # FIX: Use ID to populate No
            item_id = it.get('itemId')
            item_no = pe.id_map.get(item_id)
            if not item_no: item_no = safe_str(it.get('itemNo') or it.get('no'))

            qty = safe_float(it.get('quantity'))
            price = safe_float(it.get('unitPrice'))
            amt = safe_float(it.get('totalPrice'))
            
            if price == 0 and qty > 0 and amt > 0: price = amt / qty
            
            # Use Vendor Price if PO price is missing
            if price == 0: price = pe.vendor_prices.get(item_no, 0)
            
            if price > 0: pe.add_po(item_no, price)
            
            po_recs.append({
                'trans_date': po.get('transDate'),
                'number': po.get('number'),
                'vendor': po.get('vendorName'),
                'item_no': item_no,
                'quantity': qty,
                'unit_price': normalize_price(price),
                'total_price': normalize_price(amt if amt>0 else qty*price)
            })

    print(f'   [OK] Extracted {len(po_recs)} PO lines')
    
    # --------------------------------------------------------
    # 4. PULL PURCHASE INVOICES (For Actual Cost)
    # --------------------------------------------------------
    print(f'\n[4] PHASE 4: PURCHASE INVOICES (Limit {LIMIT_INVOICE})')
    pinvs = cl.pages('/api/purchase-invoice/list.do', {'filter.transDate.>=': start_date}, 50)
    for i, pi in enumerate(pinvs[:LIMIT_INVOICE]):
        d = cl.get('/api/purchase-invoice/detail.do', {'id': pi['id']})
        if not d or not d.get('s'): continue
        for it in (d['d'].get('detailItem') or []):
            item_no = safe_str(it.get('itemNo'))
            price = safe_float(it.get('unitPrice'))
            if price > 0: pe.add_invoice(item_no, price)
            
    # --------------------------------------------------------
    # 5. MASTER ITEMS RECONSTRUCTION
    # --------------------------------------------------------
    print('\n[5] PHASE 5: RECONSTRUCTING MASTER ITEMS')
    # Use already pulled master data from Phase 0
    # keys in master_meta: id -> dict
    
    master_recs = []
    
    for mid, m in pe.master_meta.items():
        no = safe_str(m.get('no'))
        
        # KEY: Construct price from history
        m_price = pe.get_market_price(no)
        m_cost = pe.get_replacement_cost(no)
        
        master_recs.append({
            'id': m.get('id'),
            'no': no,
            'name': normalize_item_name(m.get('name')),
            'itemType': m.get('itemType'),
            'category': m.get('itemCategoryName'),
            'unitPrice': normalize_price(m_price),
            'avgCost': normalize_price(m_cost),
            'price_source': 'History' if pe.sales_history[no] else ('PO+Markup' if pe.po_history[no] else 'Unknown')
        })
        
    print(f'   [OK] Reconstructed {len(master_recs)} master items')
    
    # --------------------------------------------------------
    # 5.5 STOCK MUTATIONS (Full Crawl)
    # --------------------------------------------------------
    print(f'\n[5.5] PHASE 5.5: STOCK MUTATIONS (Full History)')
    mutation_recs = []
    
    # Iterate over all master items to get mutations
    items_to_scan = list(pe.master_meta.items())
    print(f'   Scanning mutations for {len(items_to_scan)} items (This is slow, please wait)...')
    
    for i, (mid, m) in enumerate(items_to_scan):
        if (i+1) % 50 == 0: print(f'   Progress: {i+1}/{len(items_to_scan)}...')
        
        muts = cl.pages('/api/item/stock-mutation-history.do', {
            'itemId': mid,
            'filter.transactionDate.>=': start_date,
            'filter.transactionDate.<=': end_date
        }, 20) # Max 20 pages per item
        
        for mut in muts:
            mutation_recs.append({
                'item_no': safe_str(m.get('no')),
                'date': mut.get('transactionDate'),
                'type': mut.get('transactionType'),
                'qty_change': mut.get('mutation'),
                'cost': normalize_price(mut.get('itemCost')),
                'warehouse': mut.get('warehouseName'),
                'balance': 0 
            })
            
            # Enrich PriceEngine if cost found and missing?
            if safe_float(mut.get('itemCost')) > 0:
                pe.id_map[mid] = safe_str(m.get('no')) 
                
    print(f'   [OK] Extracted {len(mutation_recs)} mutation lines')

    # --------------------------------------------------------
    # 6. STOCK STATUS
    # --------------------------------------------------------
    print('\n[6] PHASE 6: STOCK STATUS')
    # Try bulk report first? Using list-stock for now enriched with PE
    stocks = cl.pages('/api/item/list-stock.do', {'fields': 'id,no,quantity,warehouseName'}, 100)
    
    stock_recs = []
    for s in stocks:
        no = s.get('no') or pe.id_map.get(s.get('id'), '')
        qty = safe_float(s.get('quantity'))
        
        cost = pe.get_replacement_cost(no)
        price = pe.get_market_price(no)
        
        stock_recs.append({
            'item_no': no,
            'warehouse': s.get('warehouseName') or 'Aggregated',
            'on_stock': qty,
            'avg_cost': normalize_price(cost),
            'unit_price': normalize_price(price),
            'stock_value': normalize_price(qty * cost),
            'potential_revenue': normalize_price(qty * price)
        })
        
    print(f'   [OK] Processed {len(stock_recs)} stock records')

    # --------------------------------------------------------
    # 7. EXPORT
    # --------------------------------------------------------
    print('\n[7] PHASE 7: EXPORTING')
    # OUTPUT_DIR = r'../../data/new_base_dataset_project1'
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'new_base_dataset_project1')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    pd.DataFrame(sales_recs).to_csv(os.path.join(OUTPUT_DIR, '1_Sales_Details.csv'), index=False)
    pd.DataFrame(po_recs).to_csv(os.path.join(OUTPUT_DIR, '2_PO_Details.csv'), index=False)
    pd.DataFrame(mutation_recs).to_csv(os.path.join(OUTPUT_DIR, '3_Stock_Mutations.csv'), index=False)
    pd.DataFrame(stock_recs).to_csv(os.path.join(OUTPUT_DIR, '4_Current_Stock.csv'), index=False)
    pd.DataFrame(master_recs).to_csv(os.path.join(OUTPUT_DIR, '5_Master_Items.csv'), index=False)
    
    print('   [OK] Export Complete')
    
def normalize_item_name(name):
    return str(name).strip() if name else ''

if __name__ == '__main__':
    main()
