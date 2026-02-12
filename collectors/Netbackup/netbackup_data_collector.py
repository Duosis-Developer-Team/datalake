#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetBackup Data Collector
Zerto collector mantığıyla NetBackup verilerini toplar ve JSON formatında stdout'a yazdırır.
NiFi flow'u ile uyumlu çalışır.
Port Fallback ve Config File parametresi eklenmiştir.
"""

import requests
import json
import sys
import argparse
import urllib3
import socket
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

# SSL uyarılarını devre dışı bırak
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NetBackupDataCollector:
    """NetBackup API'den veri toplayan ana sınıf"""
    
    def __init__(self, host: str, port: int = 443, username: str = None, password: str = None, token: str = None, hostname: str = None):
        """
        NetBackup collector'ı başlatır
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.token = token
        
        # Hostname belirleme
        if hostname:
            self.hostname = hostname
        else:
            try:
                self.hostname = socket.gethostbyaddr(host)[0]
            except:
                self.hostname = host
        
        # Base URL: Port bilgisini içerir
        self.base_url = f"https://{host}:{port}"
        
        self.session = requests.Session()
        self.session.verify = False
        
        # SSL Context Ayarları
        import ssl
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context
        
        class SSLAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = create_urllib3_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                kwargs['ssl_context'] = context
                return super().init_poolmanager(*args, **kwargs)
        
        self.session.mount('https://', SSLAdapter())
        
        # Authentication / Token
        # Token yoksa almayı dene, başarısız olursa exception fırlat (böylece diğer porta geçilebilir)
        if not self.token:
            if self.username and self.password:
                self.token = self.get_auth_token()
                if not self.token:
                    raise Exception(f"Authentication failed on {self.base_url}")
            else:
                raise Exception("Token or Username/Password required!")
        
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Host": self.hostname 
        })
    
    def get_auth_token(self) -> str:
        """NetBackup API'dan Bearer token al"""
        try:
            auth_url = f"{self.base_url}/netbackup/login"
            
            auth_data = {
                "userName": self.username,
                "password": self.password
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": self.hostname
            }
            
            # Bağlantı testi için timeout (5sn connect, 30sn read)
            response = self.session.post(auth_url, json=auth_data, headers=headers, timeout=(5, 30), verify=False)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data.get('token')
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection failed to {auth_url}: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON Decode Error: {str(e)}")
        
    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """API isteği gönderir"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Request Error ({url}): {e}", file=sys.stderr)
            raise
    
    def collect_jobs_data(self, since_minutes: Optional[int] = 15) -> Tuple[List[Dict], str]:
        """Jobs verilerini toplar"""
        try:
            endpoint = "/netbackup/admin/jobs"
            params = {}
            if since_minutes is not None:
                now = datetime.now(timezone.utc)
                time_limit = now - timedelta(minutes=since_minutes)
                time_limit_iso = time_limit.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                params["filter"] = f"lastUpdateTime gt {time_limit_iso}"
                params["page[limit]"] = "999"
                params["sort"] = "-lastUpdateTime"
            
            jobs_data = self.make_request(endpoint, params)
            jobs_list = []
            
            all_jobs = jobs_data.get("data", [])
            next_url = jobs_data.get("links", {}).get("next", {}).get("href")
            
            while next_url:
                try:
                    response = self.session.get(next_url, timeout=30)
                    response.raise_for_status()
                    page_data = response.json()
                    all_jobs.extend(page_data.get("data", []))
                    next_url = page_data.get("links", {}).get("next", {}).get("href")
                except requests.RequestException:
                    break
            
            for job in all_jobs:
                attrs = job.get("attributes", {})
                job_data = {k: v for k, v in job.items() if k != 'attributes'}
                job_data.update(attrs)
                jobs_list.append(job_data)
            
            server_timestamp = datetime.now(timezone.utc).isoformat()
            return jobs_list, server_timestamp
        except Exception as e:
            print(f"Jobs collection error: {e}", file=sys.stderr)
            return [], datetime.now(timezone.utc).isoformat()
    
    def collect_disk_pools_data(self) -> Tuple[List[Dict], str]:
        """Disk pools verilerini toplar"""
        try:
            endpoint = "/netbackup/storage/disk-pools"
            disk_pools_data = self.make_request(endpoint)
            disk_pools_list = []
            for item in disk_pools_data.get("data", []):
                attrs = item.get("attributes", {})
                disk_pool_data = {'id': item.get("id"), 'type': item.get("type"), **attrs}
                disk_pools_list.append(disk_pool_data)
            server_timestamp = datetime.now(timezone.utc).isoformat()
            return disk_pools_list, server_timestamp
        except Exception as e:
            print(f"Disk pools collection error: {e}", file=sys.stderr)
            return [], datetime.now(timezone.utc).isoformat()
    
    def generate_unique_timestamp(self, entity_id: str, api_timestamp: Optional[str] = None) -> str:
        if api_timestamp:
            try:
                base_timestamp = datetime.fromisoformat(api_timestamp.replace('Z', '+00:00'))
            except:
                base_timestamp = datetime.now(timezone.utc)
        else:
            base_timestamp = datetime.now(timezone.utc)
        entity_hash = hash(entity_id) % 1000000
        unique_timestamp = base_timestamp.replace(microsecond=entity_hash)
        return unique_timestamp.isoformat()
    
    def collect_all_data(self, since_minutes: Optional[int] = 15) -> List[Dict]:
        """Tüm verileri toplar"""
        print(f"SUCCESS: Connected to {self.host} on port {self.port}", file=sys.stderr)
        
        all_data = []
        # Jobs
        try:
            jobs_data, _ = self.collect_jobs_data(since_minutes)
            for job in jobs_data:
                entity_id = str(job.get('jobId', 'unknown'))
                api_timestamp = job.get('lastUpdateTime')
                unique_timestamp = self.generate_unique_timestamp(entity_id, api_timestamp)
                record = {
                    'data_type': 'netbackup_job',
                    'collection_timestamp': unique_timestamp,
                    'netbackup_host': self.host,
                    'netbackup_port': self.port,
                    **job
                }
                all_data.append(record)
        except Exception as e:
            print(f"Job processing error: {e}", file=sys.stderr)
        
        # Disk Pools
        try:
            disk_pools_data, _ = self.collect_disk_pools_data()
            for pool in disk_pools_data:
                entity_id = str(pool.get('name', 'unknown'))
                unique_timestamp = self.generate_unique_timestamp(entity_id)
                record = {
                    'data_type': 'netbackup_disk_pool',
                    'collection_timestamp': unique_timestamp,
                    'netbackup_host': self.host,
                    'netbackup_port': self.port,
                    **pool
                }
                all_data.append(record)
        except Exception as e:
            print(f"Disk pool processing error: {e}", file=sys.stderr)
            
        return all_data

def main():
    """Ana fonksiyon - Port Fallback ve Config File Destekli"""
    parser = argparse.ArgumentParser(description="NetBackup veri toplayıcı")
    parser.add_argument("--host", type=str, help="NetBackup sunucu IP adresi")
    parser.add_argument("--since-minutes", type=int, default=15, help="Son kaç dakikadaki veriler")
    parser.add_argument("--config-file", type=str, help="JSON config dosyası tam yolu")
    
    args = parser.parse_args()
    
    hosts_to_process = []
    target_ports = [443] # Default port
    username = None
    password = None
    token = None
    
    # 1. Öncelik: Command-line arguments (Host varsa config'e bakmaz)
    if args.host:
        hosts_to_process = [args.host]
        print(f"Using single host from arguments: {args.host}", file=sys.stderr)
    else:
        # 2. Config dosyasından oku
        try:
            # Eğer --config-file verildiyse SADECE ona bak
            if args.config_file:
                # Kullanıcı parametre ile yol verdiyse, listeye onu ekle
                if os.path.exists(args.config_file):
                    config_paths = [args.config_file]
                    print(f"Looking for config file at specific path: {args.config_file}", file=sys.stderr)
                else:
                    print(f"Error: Specified config file not found at {args.config_file}", file=sys.stderr)
                    sys.exit(1)
            else:
                # Verilmediyse varsayılanlara bak
                config_paths = [
                    "configuration_file.json",
                    "Datalake_Project/configuration_file.json",
                    "../Datalake_Project/configuration_file.json",
                    "./Datalake_Project/configuration_file.json",
                    "/Datalake_Project/configuration_file.json"
                ]
            
            config_loaded = False
            for config_path in config_paths:
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            netbackup_config = config.get('Netbackup', {})
                            
                            # --- Hosts (Hostname or IP) ---
                            hostname_config = netbackup_config.get('Hostname', '')
                            ip_addresses = netbackup_config.get('IpAddress', '')
                            
                            if hostname_config:
                                hosts_to_process = [h.strip() for h in hostname_config.split(',')]
                                print(f"Config loaded ({config_path}): Using Hostnames ({len(hosts_to_process)} hosts)", file=sys.stderr)
                            elif ip_addresses:
                                hosts_to_process = [ip.strip() for ip in ip_addresses.split(',')]
                                print(f"Config loaded ({config_path}): Using IPs ({len(hosts_to_process)} hosts)", file=sys.stderr)
                            
                            # --- Ports ---
                            port_config = netbackup_config.get('Port', '')
                            if port_config:
                                # String "443, 1556" -> List [443, 1556]
                                # Config dosyasındaki değer integer veya string olabilir, güvenli çevirim yapıyoruz
                                ports_str = str(port_config)
                                target_ports = [int(p.strip()) for p in ports_str.split(',') if p.strip().isdigit()]
                                print(f"Config loaded: Using Ports {target_ports}", file=sys.stderr)
                            else:
                                target_ports = [443]
                                print(f"Config loaded: No port defined, using default {target_ports}", file=sys.stderr)

                            username = netbackup_config.get('Username') or netbackup_config.get('username')
                            password = netbackup_config.get('Password') or netbackup_config.get('password')
                            token = netbackup_config.get('Bearer_token') or netbackup_config.get('bearer_token')
                            
                        config_loaded = True
                        break
                    except Exception as e:
                        print(f"Error reading config file {config_path}: {e}", file=sys.stderr)
                        continue
            
            if not config_loaded:
                print(f"Error: Configuration file not found! Searched in: {config_paths}", file=sys.stderr)
                sys.exit(1)
                
        except Exception as e:
            print(f"Config processing error: {e}", file=sys.stderr)
            sys.exit(1)
    
    if not hosts_to_process:
        print("Error: No hosts to process!", file=sys.stderr)
        sys.exit(1)

    all_results = []
    
    # --- HOST LOOP ---
    for host in hosts_to_process:
        host_success = False
        
        # --- PORT FALLBACK LOOP ---
        for port in target_ports:
            try:
                print(f"Attempting connection to {host} on port {port}...", file=sys.stderr)
                
                collector = NetBackupDataCollector(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    token=token,
                    hostname=host
                )
                
                # Veri toplamayı dene. Eğer bağlantı hatası olursa burası exception fırlatır
                # ve kod except bloğuna giderek bir sonraki portu dener.
                host_data = collector.collect_all_data(args.since_minutes)
                all_results.extend(host_data)
                
                # Buraya gelindiyse işlem başarılıdır
                host_success = True
                break  # Bu host için başarılı oldu, sonraki porta geçme
                
            except Exception as e:
                print(f"Failed to connect to {host}:{port} -> {str(e)}", file=sys.stderr)
                continue # Bu port başarısız, sıradaki portu dene
        
        if not host_success:
            print(f"ERROR: Could not connect to {host} on any of the ports {target_ports}", file=sys.stderr)
    
    # JSON çıktısı
    if all_results:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    else:
        # Hiç sonuç yoksa boş liste bas (JSON hatası almamak için)
        print("[]")

if __name__ == "__main__":
    main()
