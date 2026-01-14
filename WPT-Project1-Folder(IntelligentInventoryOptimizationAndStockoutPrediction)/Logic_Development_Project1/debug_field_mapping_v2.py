import requests, hashlib, hmac, base64, json, time, sys
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings('ignore')

print("DEBUG: Script started", flush=True)

# ============================================================
# CONFIG
# ============================================================
API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
wib = pytz.timezone('Asia/Jakarta')

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
        print("DEBUG: Connecting to API...", flush=True)
        try:
            r = requests.post('https://account.accurate.id/api/api-token.do', headers=self.headers(), timeout=10)
            print(f"DEBUG: Status {r.status_code}", flush=True)
            d = r.json()
            k = 'database' if 'database' in d.get('d',{}) else 'data usaha'
            if d.get('s'):
                self.host = d['d'][k]['host']
                print(f'✅ Connected: {self.host}', flush=True)
                return True
            print(f'❌ Connection failed: {d}', flush=True)
            return False
        except Exception as e:
            print(f"ERROR in init: {e}", flush=True)
            return False
    
    def get(self, ep, p=None):
        if not self.host:
            return None
        try:
            r = requests.get(f'{self.host}/accurate{ep}', headers=self.headers(), params=p, timeout=30)
            return r.json()
        except Exception as e:
            print(f'   Error: {e}', flush=True)
            return None
    
    def pages(self, ep, p=None, mx=5):
        p = p or {}
        data = []
        pg = 1
        while pg <= mx:
            print(f"DEBUG: Fetching page {pg} of {ep}", flush=True)
            p['sp.page'] = pg
            p['sp.pageSize'] = 100
            r = self.get(ep, p)
            if not r or not r.get('s') or not r.get('d', []):
                break
            data.extend(r['d'])
            if pg >= r.get('sp', {}).get('pageCount', 1):
                break
            pg += 1
        return data

def main():
    start_date = (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')
    end_date = datetime.now().strftime('%d/%m/%Y')
    
    print('='*70, flush=True)
    print('🔍 FIELD MAPPING DIAGNOSTIC', flush=True)
    print('='*70, flush=True)
    
    client = AccurateAPI(API_TOKEN, SIGNATURE_SECRET)
    if not client.init():
        return
    
    print('='*70, flush=True)
    print('📦 1. ITEM MASTER STRUCTURE', flush=True)
    items = client.pages('/api/item/list.do', {}, 1)
    if items:
        print(f'   ✅ Got {len(items)} items', flush=True)
        print(f'   📋 COLUMNS ({len(items[0].keys())}):', flush=True)
        for k, v in sorted(items[0].items()):
            print(f'      • {k}: {type(v).__name__} = {repr(v)[:50]}', flush=True)
    else:
        print('   ❌ No items returned', flush=True)

    # Just do items first to check connectivity
    pass

if __name__ == '__main__':
    main()
