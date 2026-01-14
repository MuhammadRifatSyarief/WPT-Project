"""
Script untuk membuktikan inkonsistensi data stok antara:
- /api/item/list-stock.do (quantity)
- /api/item/stock-mutation-history.do (mutation records)

Tujuan: Mencari item yang quantity=0 di list-stock TAPI ada mutation history
"""

import requests, hashlib, hmac, base64, time
from datetime import datetime, timedelta
import pytz

API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
wib = pytz.timezone('Asia/Jakarta')

class API:
    def __init__(self):
        self.host = None
    
    def sign(self, ts):
        return base64.b64encode(hmac.new(SIGNATURE_SECRET.encode(), ts.encode(), hashlib.sha256).digest()).decode()
    
    def headers(self):
        ts = datetime.now(wib).strftime('%d/%m/%Y %H:%M:%S')
        return {
            'Authorization': f'Bearer {API_TOKEN}',
            'X-Api-Timestamp': ts,
            'X-Api-Signature': self.sign(ts),
        }
    
    def init(self):
        r = requests.post('https://account.accurate.id/api/api-token.do', headers=self.headers())
        d = r.json()
        k = 'database' if 'database' in d.get('d',{}) else 'data usaha'
        if d.get('s'):
            self.host = d['d'][k]['host']
            print(f'Connected: {self.host}')
            return True
        return False
    
    def get(self, ep, p=None):
        r = requests.get(f'{self.host}/accurate{ep}', headers=self.headers(), params=p, timeout=30)
        return r.json()

def main():
    print("="*70)
    print("BUKTI INKONSISTENSI DATA STOK")
    print("="*70)
    
    api = API()
    if not api.init():
        return
    
    end_date = datetime.now().strftime('%d/%m/%Y')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')
    
    # Step 1: Ambil item dari list-stock dengan quantity = 0
    print("\n1. Mencari item dengan quantity = 0 di list-stock.do...")
    stocks = api.get('/api/item/list-stock.do', {'sp.pageSize': 100})
    
    if not stocks.get('s'):
        print("   Gagal ambil data stok")
        return
    
    zero_stock_items = []
    for item in stocks.get('d', []):
        qty = item.get('quantity', 0)
        if qty == 0 or qty == 0.0:
            zero_stock_items.append({
                'id': item.get('id'),
                'no': item.get('no'),
                'name': item.get('name', '')[:40],
                'quantity': qty
            })
    
    print(f"   Ditemukan {len(zero_stock_items)} item dengan quantity = 0")
    
    # Step 2: Cek mutation history untuk item dengan stock 0
    print("\n2. Mengecek mutation history untuk item yang quantity = 0...")
    print("-"*70)
    
    inconsistent_items = []
    checked = 0
    
    for item in zero_stock_items[:20]:  # Cek 20 item pertama
        checked += 1
        item_id = item['id']
        
        mutation = api.get('/api/item/stock-mutation-history.do', {
            'id': item_id,
            'startDate': start_date,
            'endDate': end_date
        })
        
        if mutation.get('s') and mutation.get('d'):
            records = mutation['d']
            total_in = sum(r.get('mutation', 0) for r in records if r.get('mutation', 0) > 0)
            total_out = sum(abs(r.get('mutation', 0)) for r in records if r.get('mutation', 0) < 0)
            
            if len(records) > 0:
                inconsistent_items.append({
                    'id': item_id,
                    'no': item['no'],
                    'name': item['name'],
                    'stock_reported': 0,
                    'mutation_count': len(records),
                    'total_in': total_in,
                    'total_out': total_out
                })
                print(f"   INKONSISTEN: Item {item['no']}")
                print(f"      - list-stock.do: quantity = 0")
                print(f"      - mutation-history: {len(records)} records, IN={total_in}, OUT={total_out}")
        
        time.sleep(0.4)  # Rate limit
    
    print("-"*70)
    print(f"\n3. HASIL:")
    print(f"   Item dicek: {checked}")
    print(f"   Item INKONSISTEN: {len(inconsistent_items)}")
    
    if inconsistent_items:
        print("\n4. BUKTI INKONSISTENSI:")
        print("-"*70)
        for item in inconsistent_items:
            print(f"   Item No: {item['no']}")
            print(f"   Stock di list-stock.do: 0")
            print(f"   Mutation records: {item['mutation_count']} transaksi")
            print(f"   Total masuk: {item['total_in']}, Total keluar: {item['total_out']}")
            print()
    else:
        print("\n   Tidak ditemukan inkonsistensi - item dengan stock 0 memang tidak ada mutasi")

if __name__ == '__main__':
    main()
