import requests, hashlib, hmac, base64, time, json
from datetime import datetime
import pytz

# CONFIG
API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
wib = pytz.timezone('Asia/Jakarta')

def headers():
    ts = datetime.now(wib).strftime('%d/%m/%Y %H:%M:%S')
    sign = base64.b64encode(hmac.new(SIGNATURE_SECRET.encode(), ts.encode(), hashlib.sha256).digest()).decode()
    return {'Authorization': f'Bearer {API_TOKEN}', 'X-Api-Timestamp': ts, 'X-Api-Signature': sign, 'Content-Type': 'application/json'}

def debug_receipt():
    print("Connecting...")
    r = requests.post('https://account.accurate.id/api/api-token.do', headers=headers()).json()
    if not r.get('s'): return print("Auth failed")
    host = r['d'][('database' if 'database' in r['d'] else 'data usaha')]['host']
    
    # Get 1 receipt
    print(f"Fetching 1 receipt list from {host}...")
    lst = requests.get(f'{host}/accurate/api/receive-item/list.do', headers=headers(), params={'sp.pageSize': 1}).json()
    if not lst.get('d'): return print("No receipts found")
    
    rid = lst['d'][0]['id']
    print(f"Inspecting Receipt ID: {rid}")
    
    # Get Detail
    det = requests.get(f'{host}/accurate/api/receive-item/detail.do', headers=headers(), params={'id': rid}).json()
    
    print("\nRAW JSON (First 1000 chars of structure):")
    print(json.dumps(det, indent=2))

if __name__ == '__main__':
    debug_receipt()
