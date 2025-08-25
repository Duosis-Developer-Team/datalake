import json
import requests
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus, urljoin
import warnings
from urllib3.exceptions import InsecureRequestWarning

# SSL doğrulaması (verify=False) devre dışı bırakıldığında oluşan uyarıyı bastırır.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

class VeeamAPI:
    def __init__(self, params):
        self.params = {}
        self.token = None
        self._set_params(params)

    def _set_params(self, params):
        required_fields = ['api_endpoint', 'user', 'password', 'created_after', 'lastrun_after', 'limit']
        if not isinstance(params, dict):
            raise ValueError('Parametreler bir sözlük (dictionary) olmalıdır.')
        for field in required_fields:
            if field not in params or not params.get(field):
                raise ValueError(f'Gerekli parametre ayarlanmamış veya boş: {field}.')
        self.params = params
        if not self.params['api_endpoint'].endswith('/'):
            self.params['api_endpoint'] += '/'
        created_after = int(self.params['created_after'])
        if not 1 <= created_after <= 365: raise ValueError(f'Geçersiz "created_after" parametresi: {created_after}.')
        self.params['created_after'] = created_after
        lastrun_after = int(self.params['lastrun_after'])
        if not 1 <= lastrun_after <= 365: raise ValueError(f'Geçersiz "lastrun_after" parametresi: {lastrun_after}.')
        self.params['lastrun_after'] = lastrun_after
        limit = int(self.params['limit'])
        if not 1 <= limit <= 10000: raise ValueError(f'Geçersiz "limit" parametresi: {limit}.')
        self.params['limit'] = limit

    def login(self):
        url = urljoin(self.params['api_endpoint'], 'api/oauth2/token')
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'x-api-version': '1.0-rev2'}
        data = {'grant_type': 'password', 'username': self.params['user'], 'password': self.params['password']}
        proxies = {'http': self.params.get('http_proxy'), 'https': self.params.get('http_proxy')}
        
        # --- DEĞİŞİKLİK ---
        # SSL doğrulaması kalıcı olarak kapatıldı.
        verify_ssl = False
        
        try:
            response = requests.post(url, headers=headers, data=data, proxies=proxies, verify=verify_ssl)
            response.raise_for_status()
            resp_json = response.json()
            if 'access_token' not in resp_json:
                raise ValueError('Kimlik doğrulama yanıtı "access_token" içermiyor.')
            self.token = resp_json['access_token']
        except requests.exceptions.RequestException as e:
            raise Exception(f'Giriş başarısız oldu: {e}')
        except json.JSONDecodeError:
            raise Exception('Oturum açma için kimlik doğrulama token\'ı çözümlenemedi.')

    def _request(self, url):
        if not self.token:
            raise Exception('İstek yapmadan önce giriş yapılmalıdır.')
        headers = {'Authorization': f'Bearer {self.token}', 'x-api-version': '1.2-rev0'}
        proxies = {'http': self.params.get('http_proxy'), 'https': self.params.get('http_proxy')}

        # --- DEĞİŞİKLİK ---
        # SSL doğrulaması kalıcı olarak kapatıldı.
        verify_ssl = False

        try:
            response = requests.get(url, headers=headers, proxies=proxies, verify=verify_ssl)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f'İstek başarısız oldu: {e}')
        except json.JSONDecodeError:
            raise Exception('API\'den alınan yanıt çözümlenemedi.')

    def get_all_pages(self, relative_or_full_url):
        all_data = []
        next_url = relative_or_full_url
        while next_url:
            page = self._request(next_url)
            if page and 'data' in page: all_data.extend(page.get('data', []))
            next_url = None
            if page and isinstance(page.get('links'), list):
                for link in page['links']:
                    if link.get('rel') == 'next':
                        next_url = link.get('href')
                        break
        return {'data': all_data}

    def get_metrics_data(self):
        data = {}
        now = datetime.now(timezone.utc)
        start_date_sessions = (now - timedelta(days=self.params['created_after'])).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_date_jobs = (now - timedelta(days=self.params['lastrun_after'])).strftime('%Y-%m-%dT%H:%M:%SZ')
        limit_q = f"&limit={self.params['limit']}"
        endpoints = {
            'proxies': 'api/v1/backupInfrastructure/proxies',
            'managedServers': 'api/v1/backupInfrastructure/managedServers',
            'repositories_states': 'api/v1/backupInfrastructure/repositories/states',
            'jobs_states': f"api/v1/jobs/states?lastRunAfterFilter={quote_plus(start_date_jobs)}{limit_q}",
            'sessions': f"api/v1/sessions?createdAfterFilter={quote_plus(start_date_sessions)}{limit_q}"
        }
        for key, relative_url in endpoints.items():
            full_url = urljoin(self.params['api_endpoint'], relative_url)
            if key in ['sessions', 'jobs_states']:
                data[key] = self.get_all_pages(full_url)
            else:
                data[key] = self._request(full_url)
        return data

def execute_veeam_collection(params):
    try:
        veeam_client = VeeamAPI(params)
        veeam_client.login()
        metrics = veeam_client.get_metrics_data()
        print("Metrikler başarıyla toplandı.")
        return metrics
    except Exception as e:
        error_message = str(e)
        if not error_message.endswith('.'): error_message += '.'
        print(f'[ VEEAM ] HATA: {error_message}', file=sys.stderr)
        return {'error': error_message}

if __name__ == '__main__':
    CONFIG_FILE_PATH = "/Datalake_Project/configuration_file.json"
    OUTPUT_FILE_PATH = "output.json"
    
    result_data = {}

    try:
        print(f"Yapılandırma dosyası okunuyor: {CONFIG_FILE_PATH}")
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)
        
        print("Yapılandırma dosyası işleniyor...")
        if 'Veeam' not in raw_config:
            raise KeyError("Yapılandırma dosyasında 'Veeam' anahtarı bulunamadı.")
        
        veeam_config = raw_config['Veeam']

        if 'ips' not in veeam_config:
            raise KeyError("'Veeam' nesnesi içinde 'ips' anahtarı bulunamadı.")
            
        api_ip = veeam_config['ips']
        api_endpoint = f"https://{api_ip}:9419"

        params_for_api = {
            'api_endpoint': api_endpoint,
            'user': veeam_config.get('user'),
            'password': veeam_config.get('password'),
            'created_after': veeam_config.get('created_after'),
            'lastrun_after': veeam_config.get('lastrun_after'),
            'limit': veeam_config.get('limit'),
            'http_proxy': veeam_config.get('http_proxy', '')
        }

        result_data = execute_veeam_collection(params_for_api)

    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        error_msg = f"Yapılandırma hatası: {e}"
        print(f"[ VEEAM ] KRİTİK HATA: {error_msg}", file=sys.stderr)
        result_data = {'error': error_msg}
    except Exception as e:
        error_msg = f"Beklenmedik bir hata oluştu: {e}"
        print(f"[ VEEAM ] KRİTİK HATA: {error_msg}", file=sys.stderr)
        result_data = {'error': error_msg}

    try:
        print(f"Sonuçlar '{OUTPUT_FILE_PATH}' dosyasına yazılıyor...")
        with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)
        print("İşlem başarıyla tamamlandı.")
    except IOError as e:
        print(f"[ VEEAM ] KRİTİK HATA: Çıktı dosyası yazılamadı: {e}", file=sys.stderr)
