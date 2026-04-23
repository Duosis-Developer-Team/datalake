import requests
import json
import time
import os

# --- Konfigürasyon ---
TENANT_ID = "<TENANT_ID>"
CLIENT_ID = "<CLIENT_ID>"
CLIENT_SECRET = "<CLIENT_SECRET>"
CRM_URL = "https://<ORG>.crm4.dynamics.com"
API_VERSION = "v9.2"

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
API_BASE_URL = f"{CRM_URL}/api/data/{API_VERSION}/"

# Sadece Standart Ürün ve Fiyat Listesi Katalogları
ENDPOINTS = [
    "products",
    "pricelevels",
    "productpricelevels"
]

def get_access_token():
    payload = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': f"{CRM_URL}/.default"
    }
    
    start_time = time.time()
    response = requests.post(TOKEN_URL, data=payload)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print(f"[-] Token alınamadı! Status: {response.status_code}")
        return None

def fetch_and_save_data(token):
    headers = {
        'Authorization': f'Bearer {token}',
        'OData-MaxVersion': '4.0',
        'OData-Version': '4.0',
        'Accept': 'application/json',
        'Prefer': 'odata.include-annotations="*"'
    }

    print("-" * 75)
    print(f"{'ENDPOINT (CATALOG)':<20} | {'STATUS':<8} | {'RECORDS':<8} | {'FILE'}")
    print("-" * 75)

    for endpoint in ENDPOINTS:
        url = f"{API_BASE_URL}{endpoint}"
        filename = f"raw_catalog_{endpoint}.json"
        
        try:
            # Not: Ürün kataloğu geniş olabileceği için pagination'a (veri sayfalama) takılabilirsiniz.
            # Şimdilik discovery amaçlı ilk batch'i (sayfayı) alıyoruz.
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                record_count = len(data.get('value', []))
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                print(f"{endpoint:<20} | {200:<8} | {record_count:<8} | {filename}")
            else:
                print(f"{endpoint:<20} | {response.status_code:<8} | {'N/A':<8} | {'- Error -'}")
                
        except Exception as e:
            print(f"{endpoint:<20} | {'ERROR':<8} | {'N/A':<8} | {str(e)[:20]}")

    print("-" * 75)

if __name__ == "__main__":
    token = get_access_token()
    if token:
        fetch_and_save_data(token)
