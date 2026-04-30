import requests
import json
import time
import os

# --- Konfigürasyon ---
TENANT_ID = ""
CLIENT_ID = ""
CLIENT_SECRET = "" 
CRM_URL = ""
API_VERSION = "v9.2"

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
API_BASE_URL = f"{CRM_URL}/api/data/{API_VERSION}/"

# Toplanacak veri kaynakları
# msdyn_projects 404 döndüğü için alternatifleri listeye ekledim (salesorders = Siparişler/Projeler)
ENDPOINTS = [
    "accounts",
    "opportunities",
    "quotes",
    "salesorders" 
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
        elapsed = round((time.time() - start_time) * 1000, 2)
        print(f"[+] Token başarıyla alındı. ({elapsed} ms)")
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
    print(f"{'ENDPOINT':<20} | {'STATUS':<8} | {'RECORDS':<8} | {'SIZE (KB)':<10} | {'FILE'}")
    print("-" * 75)

    for endpoint in ENDPOINTS:
        url = f"{API_BASE_URL}{endpoint}"
        filename = f"raw_{endpoint}.json"
        
        start_time = time.time()
        try:
            response = requests.get(url, headers=headers)
            elapsed = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                data = response.json()
                record_count = len(data.get('value', []))
                size_kb = round(len(response.text) / 1024, 2)
                
                # Her endpoint için ayrı dosya yazımı
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                print(f"{endpoint:<20} | {200:<8} | {record_count:<8} | {size_kb:<10} | {filename}")
            else:
                print(f"{endpoint:<20} | {response.status_code:<8} | {'N/A':<8} | {'N/A':<10} | {'- Error -'}")
                
        except Exception as e:
            print(f"{endpoint:<20} | {'ERROR':<8} | {'N/A':<8} | {'N/A':<10} | {str(e)[:20]}")

    print("-" * 75)

if __name__ == "__main__":
    token = get_access_token()
    if token:
        fetch_and_save_data(token)
