import json
import requests
import argparse
import sys
import re
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse

# SSL sertifika hatalarını bastırmak için (sadece test ortamlarında önerilir)
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def camel_to_snake(name):
    """camelCase bir string'i snake_case'e çevirir."""
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def normalize_timestamp(ts_string):
    """Gelen herhangi bir ISO formatındaki zaman damgası string'ini
       milisaneyeli standart UTC (Z) formatına çevirir."""
    if not ts_string:
        return None
    try:
        # Gelen string'i bir datetime objesine çevir
        dt_object = isoparse(ts_string)
        # UTC'ye dönüştür
        dt_utc = dt_object.astimezone(timezone.utc)
        # Milisaniyeli ve 'Z' ile biten standart formata çevir
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    except (ValueError, TypeError):
        # Eğer format bozuksa veya None ise orijinal halini koru
        return ts_string

class VeeamAPIClient:
    """
    Veeam Backup & Replication REST API ile etkileşim kurmak için bir istemci.
    """
    def __init__(self, ip_address, user, password, port=9419):
        self.api_endpoint = f"https://{ip_address}:{port}/api/"
        self.user = user
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.session.verify = False

    def login(self):
        url = self.api_endpoint + "oauth2/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'x-api-version': '1.0-rev2'}
        data = {'grant_type': 'password', 'username': self.user, 'password': self.password}
        try:
            response = self.session.post(url, headers=headers, data=data)
            response.raise_for_status()
            response_json = response.json()
            if 'access_token' not in response_json:
                raise ValueError("Giriş yanıtında 'access_token' bulunamadı.")
            self.token = response_json['access_token']
            print(f"INFO: [{self.api_endpoint.split('/')[2]}] Başarıyla giriş yapıldı.", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Giriş başarısız: {e}")

    def _request(self, method, relative_url, **kwargs):
        if not self.token:
            raise PermissionError("İstek yapmadan önce giriş yapılmalı.")
        url = self.api_endpoint + relative_url
        headers = {'Authorization': f'Bearer {self.token}', 'x-api-version': '1.2-rev0', 'Accept': 'application/json'}
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            if response.text:
                return response.json()
            return None
        except json.JSONDecodeError:
            raise ValueError(f"API'den gelen yanıt JSON formatında değil: {response.text}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API isteği başarısız ({url}): {e}")

    def get_all_pages(self, relative_url):
        results = []
        next_url = self.api_endpoint + relative_url
        while next_url:
            current_relative_url = next_url.replace(self.api_endpoint, "")
            page = self._request('GET', current_relative_url)
            if page and 'data' in page:
                results.extend(page.get('data', []))
            next_url = None
            if page and 'links' in page and isinstance(page['links'], list):
                for link in page['links']:
                    if link.get('rel') == 'next':
                        next_url = link.get('href')
                        break
        return {"data": results}

    def get_all_metrics(self, created_after, lastrun_after, limit):
        all_data = {}
        limit_q = f"limit={limit}"
        sessions_url = f"v1/sessions?{limit_q}"
        if created_after > 0:
            start_date_sessions = (datetime.utcnow() - timedelta(days=created_after)).isoformat() + "Z"
            sessions_url += f"&createdAfterFilter={start_date_sessions}"
        jobs_states_url = f"v1/jobs/states?{limit_q}"
        if lastrun_after > 0:
            start_date_jobs = (datetime.utcnow() - timedelta(days=lastrun_after)).isoformat() + "Z"
            jobs_states_url += f"&lastRunAfterFilter={start_date_jobs}"
        endpoints = {
            'proxies': 'v1/backupInfrastructure/proxies',
            'managedServers': 'v1/backupInfrastructure/managedServers',
            'repositories_states': 'v1/backupInfrastructure/repositories/states',
            'jobs_states': jobs_states_url,
            'sessions': sessions_url
        }
        print(f"INFO: [{self.api_endpoint.split('/')[2]}] Metrikler toplanıyor...", file=sys.stderr)
        for key, relative_url in endpoints.items():
            try:
                print(f"INFO: - {key} verisi alınıyor...", file=sys.stderr)
                result_data = None
                if key in ['sessions', 'jobs_states']:
                    result_data = self.get_all_pages(relative_url)
                else:
                    result_data = self._request('GET', relative_url)
                if result_data and isinstance(result_data.get("data"), list):
                    for item in result_data["data"]:
                        item['data_type'] = key
                all_data[key] = result_data
            except Exception as e:
                print(f"HATA: '{key}' verisi alınırken sorun oluştu: {e}", file=sys.stderr)
                all_data[key] = {"error": str(e)}
        return all_data

def load_config(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Bilgi: Konfigürasyon dosyası bulunamadı: {file_path}. Komut satırı argümanları kullanılacak.", file=sys.stderr)
        return {}
    except json.JSONDecodeError:
        print(f"Hata: Konfigürasyon dosyası geçerli bir JSON formatında değil: {file_path}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Veeam API'den genel metrikleri çeken betik. Komut satırı argümanları config dosyasını ezer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--config-file', type=str, default='/Datalake_Project/configuration_file.json', help='Temel ayarları içeren JSON konfigürasyon dosyasının yolu.')
    parser.add_argument('--host', type=str, help='Veeam sunucu IP adresi (config dosyasını ezer).')
    parser.add_argument('--username', type=str, help='Kullanıcı adı (config dosyasını ezer).')
    parser.add_argument('--password', type=str, help='Parola (config dosyasını ezer).')
    args = parser.parse_args()
    config = load_config(args.config_file)
    veeam_config = config.get("Veeam", {})
    user = args.username if args.username else veeam_config.get("user")
    password = args.password if args.password else veeam_config.get("password")
    ip = args.host if args.host else veeam_config.get("ip")
    created_after = veeam_config.get("created_after", 7)
    lastrun_after = veeam_config.get("lastrun_after", 7)
    limit = veeam_config.get("limit", 1000)
    if not all([user, password, ip]):
        print("Hata: 'user', 'password' ve 'ip' bilgileri ya komut satırından ya da config dosyasından sağlanmalıdır.", file=sys.stderr)
        sys.exit(1)

    final_db_records = []
    collection_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    print(f"INFO: --- {ip} için işlem başlatılıyor ---", file=sys.stderr)
    try:
        client = VeeamAPIClient(ip_address=ip, user=user, password=password)
        client.login()
        metrics_data = client.get_all_metrics(
            created_after=created_after,
            lastrun_after=lastrun_after,
            limit=limit
        )
        if metrics_data:
            timestamp_fields = ['lastRun', 'nextRun', 'creationTime', 'endTime']
            for category_name, category_data in metrics_data.items():
                if category_data and isinstance(category_data.get("data"), list):
                    for record in category_data["data"]:
                        # Zaman damgası alanlarını normalize et (orijinal camelCase isimleriyle)
                        for ts_field in timestamp_fields:
                            if ts_field in record:
                                record[ts_field] = normalize_timestamp(record[ts_field])
                        
                        flat_record = record.copy()
                        if 'server' in flat_record and isinstance(flat_record.get('server'), dict):
                            server_details = flat_record.pop('server')
                            for key, value in server_details.items():
                                new_key = f"server_{key}"
                                flat_record[new_key] = value
                        if 'result' in flat_record and isinstance(flat_record.get('result'), dict):
                            result_details = flat_record.pop('result')
                            for key, value in result_details.items():
                                new_key = f"result_{key}"
                                flat_record[new_key] = value
                        
                        db_record = {camel_to_snake(key): value for key, value in flat_record.items()}
                        db_record['collection_time'] = collection_timestamp
                        db_record['source_ip'] = ip
                        final_db_records.append(db_record)
        print(f"INFO: [{ip}] Tüm metrikler başarıyla alındı ve veritabanı formatına dönüştürüldü.", file=sys.stderr)
    except Exception as e:
        print(f"Hata: {ip} işlenirken bir sorun oluştu: {e}", file=sys.stderr)
        final_db_records.append({
            "collection_time": collection_timestamp,
            "source_ip": ip,
            "status": "error",
            "message": str(e)
        })
    print(json.dumps(final_db_records, indent=4, ensure_ascii=False))
    print("\nINFO: Veri başarıyla standart çıktıya yazdırıldı.", file=sys.stderr)

if __name__ == "__main__":
    main()
