#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetBackup Data Collector
Zerto collector mantığıyla NetBackup verilerini toplar ve JSON formatında stdout'a yazdırır.
NiFi flow'u ile uyumlu çalışır.
"""

import requests
import json
import sys
import argparse
import urllib3
import socket
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

# SSL uyarılarını devre dışı bırak
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NetBackupDataCollector:
    """NetBackup API'den veri toplayan ana sınıf"""
    
    def __init__(self, host: str, username: str = None, password: str = None, token: str = None, hostname: str = None):
        self.host = host
        self.username = username
        self.password = password
        self.token = token
        
        # Config dosyasından gelen Hostname bilgisi varsa onu kullan, yoksa host parametresini kullan
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = host
        
        # URL oluşturulurken Config'den gelen "Hostname" (FQDN) kullanılır
        self.base_url = f"https://{self.hostname}"
        self.session = requests.Session()
        
        # SSL doğrulamasını tamamen devre dışı bırak
        self.session.verify = False
        
        # SSL hostname doğrulamasını devre dışı bırak
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
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
        
        # Token işlemleri
        if not self.token:
            if self.username and self.password:
                # print(f"Token alınıyor... {self.base_url}", file=sys.stderr)
                self.token = self.get_auth_token()
                if not self.token:
                    raise Exception("NetBackup authentication başarısız!")
            else:
                raise Exception("Token veya username/password bilgileri gerekli!")
        
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Host": self.hostname
        })
    
    def get_auth_token(self) -> str:
        try:
            auth_url = f"{self.base_url}/netbackup/login"
            auth_data = {
                "userName": self.username,
                "password": self.password
            }
            # Headers explicit olarak Host içerir
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": self.hostname
            }
            
            response = self.session.post(auth_url, json=auth_data, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            return response.json().get('token')
                
        except Exception as e:
            print(f"Token hatası ({auth_url}): {e}", file=sys.stderr)
            return None
        
    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API hatası ({url}): {e}", file=sys.stderr)
            raise
    
    def collect_jobs_data(self, since_minutes: Optional[int] = 60) -> Tuple[List[Dict], str]:
        try:
            endpoint = "/netbackup/admin/jobs"
            params = {}
            
            if since_minutes is not None:
                now = datetime.now(timezone.utc)
                time_limit = now - timedelta(minutes=since_minutes)
                # NetBackup API formatı
                time_limit_iso = time_limit.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                
                # OData filtresi
                params["filter"] = f"lastUpdateTime gt {time_limit_iso}"
                params["page[limit]"] = "999"
                params["sort"] = "-lastUpdateTime"
            
            jobs_data = self.make_request(endpoint, params)
            jobs_list = []
            
            all_jobs = jobs_data.get("data", [])
            next_url = jobs_data.get("links", {}).get("next", {}).get("href")
            
            # Pagination loop
            while next_url:
                try:
                    response = self.session.get(next_url, timeout=30)
                    response.raise_for_status()
                    page_data = response.json()
                    all_jobs.extend(page_data.get("data", []))
                    next_url = page_data.get("links", {}).get("next", {}).get("href")
                except:
                    break
            
            for job in all_jobs:
                attrs = job.get("attributes", {})
                # Job verilerini düzleştir
                job_data = {
                    'id': job.get("id"),
                    'type': job.get("type"),
                    'jobId': attrs.get("jobId"),
                    'policyName': attrs.get("policyName"),
                    'clientName': attrs.get("clientName"),
                    'state': attrs.get("state"),
                    'status': attrs.get("status"),
                    'jobType': attrs.get("jobType"),
                    'startTime': attrs.get("startTime"),
                    'endTime': attrs.get("endTime"),
                    'lastUpdateTime': attrs.get("lastUpdateTime"),
                    'kilobytesTransferred': attrs.get("kilobytesTransferred"),
                    'percentComplete': attrs.get("percentComplete"),
                    'parentJobId': attrs.get("parentJobId")
                }
                # İhtiyaç duyulan tüm diğer alanlar eklenebilir
                jobs_list.append(job_data)
            
            server_timestamp = datetime.now(timezone.utc).isoformat()
            return jobs_list, server_timestamp
            
        except Exception as e:
            print(f"Jobs veri toplama hatası: {e}", file=sys.stderr)
            return [], datetime.now(timezone.utc).isoformat()
    
    def collect_disk_pools_data(self) -> Tuple[List[Dict], str]:
        try:
            endpoint = "/netbackup/storage/disk-pools"
            disk_pools_data = self.make_request(endpoint)
            disk_pools_list = []
            
            for item in disk_pools_data.get("data", []):
                attrs = item.get("attributes", {})
                disk_volumes = attrs.get("diskVolumes", [{}])[0] if attrs.get("diskVolumes") else {}
                
                disk_pool_data = {
                    'id': item.get("id"),
                    'type': item.get("type"),
                    'name': attrs.get("name"),
                    'usedCapacityBytes': attrs.get("usedCapacityBytes"),
                    'availableSpaceBytes': attrs.get("availableSpaceBytes"),
                    'rawSizeBytes': attrs.get("rawSizeBytes"),
                    'diskPoolState': attrs.get("diskPoolState")
                }
                disk_pools_list.append(disk_pool_data)
            
            server_timestamp = datetime.now(timezone.utc).isoformat()
            return disk_pools_list, server_timestamp
            
        except Exception as e:
            print(f"Disk pools veri toplama hatası: {e}", file=sys.stderr)
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
    
    def collect_all_data(self, since_minutes: Optional[int] = 60) -> List[Dict]:
        all_data = []
        
        # Jobs
        jobs_data, _ = self.collect_jobs_data(since_minutes)
        for job in jobs_data:
            entity_id = job.get('id') or str(job.get('jobId'))
            unique_ts = self.generate_unique_timestamp(entity_id, job.get('lastUpdateTime'))
            all_data.append({
                'data_type': 'netbackup_job',
                'collection_timestamp': unique_ts,
                'netbackup_host': self.hostname, # Config'den gelen hostname'i bas
                **job
            })
            
        # Pools
        pools_data, _ = self.collect_disk_pools_data()
        for pool in pools_data:
            entity_id = pool.get('id') or pool.get('name')
            unique_ts = self.generate_unique_timestamp(entity_id)
            all_data.append({
                'data_type': 'netbackup_disk_pool',
                'collection_timestamp': unique_ts,
                'netbackup_host': self.hostname, # Config'den gelen hostname'i bas
                **pool
            })
            
        return all_data

def main():
    parser = argparse.ArgumentParser()
    # Argümanlar
    parser.add_argument("--host", type=str)
    parser.add_argument("--hostname", type=str)
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    parser.add_argument("--token", type=str)
    parser.add_argument("--since-minutes", type=int, default=60, help="Default 60 dk yapıldı")
    args = parser.parse_args()
    
    hosts_to_process = []
    hostnames = [] # Eşleşen FQDN listesi
    username = None
    password = None
    token = None
    
    # 1. CLI Önceliği
    if args.host:
        hosts_to_process = [args.host]
        hostnames = [args.hostname if args.hostname else args.host]
        username = args.username
        password = args.password
        token = args.token
    else:
        # 2. Config Dosyası
        try:
            config_paths = ["configuration_file.json", "Datalake_Project/configuration_file.json", "../configuration_file.json"]
            loaded = False
            for path in config_paths:
                try:
                    with open(path, 'r') as f:
                        config = json.load(f)
                        nb_conf = config.get('Netbackup', {})
                        
                        # --- KRİTİK BÖLÜM: Hostname Önceliği ---
                        hostname_conf = nb_conf.get('Hostname', '')
                        ip_conf = nb_conf.get('IpAddress', '')
                        
                        # Eğer config dosyasında Hostname tanımlıysa onu al
                        if hostname_conf:
                            hostnames = [h.strip() for h in hostname_conf.split(',')]
                            hosts_to_process = hostnames # URL için de bunu kullanacağız
                            print(f"Config'den Hostname okundu: {hostnames}", file=sys.stderr)
                        elif ip_conf:
                            # Yoksa mecburen IP
                            hosts_to_process = [i.strip() for i in ip_conf.split(',')]
                            hostnames = hosts_to_process
                            print(f"UYARI: Config'de Hostname yok, IP kullanılıyor: {hosts_to_process}", file=sys.stderr)
                            
                        username = nb_conf.get('Username') or nb_conf.get('username')
                        password = nb_conf.get('Password') or nb_conf.get('password')
                        token = nb_conf.get('Bearer_token')
                        loaded = True
                        break
                except FileNotFoundError:
                    continue
            
            if not loaded:
                print("Hata: Config dosyası bulunamadı.", file=sys.stderr)
                sys.exit(1)
                
        except Exception as e:
            print(f"Config okuma hatası: {e}", file=sys.stderr)
            sys.exit(1)

    # İşlem döngüsü
    all_results = []
    for i, host in enumerate(hosts_to_process):
        try:
            # Doğru hostname'i seç
            current_hostname = hostnames[i] if i < len(hostnames) else host
            
            print(f"Veri toplanıyor... Hedef: {current_hostname} (Süre: {args.since_minutes}dk)", file=sys.stderr)
            
            collector = NetBackupDataCollector(
                host=current_hostname, # URL buraya gider: https://nbmaster03dc13.blt.vc
                username=username,
                password=password,
                token=token,
                hostname=current_hostname
            )
            
            data = collector.collect_all_data(since_minutes=args.since_minutes)
            all_results.extend(data)
            
        except Exception as e:
            print(f"Hata ({host}): {e}", file=sys.stderr)
            continue
            
    print(json.dumps(all_results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
