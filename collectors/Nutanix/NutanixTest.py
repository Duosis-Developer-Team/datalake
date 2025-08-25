#https://10.34.2.205:9440/PrismGateway/services/rest/v1/protection_domains/Bulutistan-1Days_14RP/dr_snapshots?fullDetails=true&_=1744362399259&projection=stats%2Calerts&filterCriteria=state!%3DEXPIRED
import requests
import json

# Konfigürasyon dosyasını oku
json_file_path = "/Datalake_Project/configuration_file.json"
with open(json_file_path, "r") as file:
    config = json.load(file)

# Nutanix Prism API erişim bilgileri
nutanix_config = config["Nutanix"]

# PRISM_IP değeri birden fazla IP içerebilir
prism_ip_string = nutanix_config['PRISM_IP']
prism_ips = [ip.strip() for ip in prism_ip_string.split(",") if ip.strip()] if prism_ip_string else []

USERNAME = nutanix_config["USERNAME"]
PASSWORD = nutanix_config["PASSWORD"]
AUTH = (USERNAME, PASSWORD)

# SSL uyarılarını bastır
requests.packages.urllib3.disable_warnings()

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Her bir IP için istek yap
for prism_ip in prism_ips:
    url = f"https://{prism_ip}:9440/PrismGateway/services/rest/v2.0/protection_domains/Bulutistan-1Days_14RP/dr_snapshots"

    try:
        response = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
        response.raise_for_status()
        data = response.json()

        output_file = f"testOutput_{prism_ip.replace('.', '_')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"✅ Response saved to {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed for {prism_ip}: {e}")
    except ValueError as e:
        print(f"❌ Failed to decode JSON from {prism_ip}: {e}")
