#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetBackup Data Collector
Hem NiFi (IP input) hem Manuel (Hostname input) kullanimda
Config dosyasindan dogru eslesmeyi yaparak Rapora IP basar.
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
    
    def __init__(self, connect_host: str, report_ip: str, username: str = None, password: str = None, token: str = None):
        """
        Args:
            connect_host: Bağlantı kurulacak FQDN (SSL için)
            report_ip: JSON çıktısında 'netbackup_host' alanına yazılacak IP
        """
        self.connect_host = connect_host
        self.report_ip = report_ip 
        
        self.username = username
        self.password = password
        self.token = token
        
        # URL oluşturulurken Hostname kullanılır
        self.base_url = f"https://{self.connect_host}"
        self.session = requests.Session()
        self.session.verify = False
        
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
        
        if not self.token:
            if self.username and self.password:
                self.token = self.get_auth_token()
                if not self.token:
                    raise Exception("NetBackup authentication başarısız!")
            else:
                raise Exception("Token veya username/password bilgileri gerekli!")
        
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Host": self.connect_host
        })
    
    def get_auth_token(self) -> str:
        try:
            auth_url = f"{self.base_url}/netbackup/login"
            auth_data = {"userName": self.username, "password": self.password}
            headers = {"Content-Type": "application/json", "Accept": "application/json", "Host": self.connect_host}
            
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
    
    def collect_jobs_data(self, since_minutes: Optional[int] = 30) -> Tuple[List[Dict], str]:
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
                except:
                    break
            
            for job in all_jobs:
                attrs = job.get("attributes", {})
                job_data = {
                    'id': job.get("id"), 'type': job.get("type"), 'jobId': attrs.get("jobId"),
                    'policyName': attrs.get("policyName"), 'clientName': attrs.get("clientName"),
                    'state': attrs.get("state"), 'status': attrs.get("status"), 'jobType': attrs.get("jobType"),
                    'startTime': attrs.get("startTime"), 'endTime': attrs.get("endTime"),
                    'lastUpdateTime': attrs.get("lastUpdateTime"), 'kilobytesTransferred': attrs.get("kilobytesTransferred"),
                    'percentComplete': attrs.get("percentComplete"), 'parentJobId': attrs.get("parentJobId")
                }
                jobs_list.append(job_data)
            return jobs_list, datetime.now(timezone.utc).isoformat()
        except Exception as e:
            print(f"Jobs hata: {e}", file=sys.stderr)
            return [], datetime.now(timezone.utc).isoformat()
    
    def collect_disk_pools_data(self) -> Tuple[List[Dict], str]:
        try:
            endpoint = "/netbackup/storage/disk-pools"
            disk_pools_data = self.make_request(endpoint)
            disk_pools_list = []
            for item in disk_pools_data.get("data", []):
                attrs = item.get("attributes", {})
                disk_pool_data = {
                    'id': item.get("id"), 'type': item.get("type"), 'name': attrs.get("name"),
                    'usedCapacityBytes': attrs.get("usedCapacityBytes"), 'availableSpaceBytes': attrs.get("availableSpaceBytes"),
                    'rawSizeBytes': attrs.get("rawSizeBytes"), 'diskPoolState': attrs.get("diskPoolState")
                }
                disk_pools_list.append(disk_pool_data)
            return disk_pools_list, datetime.now(timezone.utc).isoformat()
        except Exception as e:
            print(f"Pools hata: {e}", file=sys.stderr)
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
    
    def collect_all_data(self, since_minutes: Optional[int] = 30) -> List[Dict]:
        all_data = []
        jobs_data, _ = self.collect_jobs_data(since_minutes)
        for job in jobs_data:
            entity_id = job.get('id') or str(job.get('jobId'))
            unique_ts = self.generate_unique_timestamp(entity_id, job.get('lastUpdateTime'))
            all_data.append({
                'data_type': 'netbackup_job', 'collection_timestamp': unique_ts,
                'netbackup_host': self.report_ip, # IP BASAR
                **job
            })
            
        pools_data, _ = self.collect_disk_pools_data()
        for pool in pools_data:
            entity_id = pool.get('id') or pool.get('name')
            unique_ts = self.generate_unique_timestamp(entity_id)
            all_data.append({
                'data_type': 'netbackup_disk_pool', 'collection_timestamp': unique_ts,
                'netbackup_host': self.report_ip, # IP BASAR
                **pool
            })
        return all_data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str)
    parser.add_argument("--hostname", type=str)
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    parser.add_argument("--token", type=str)
    parser.add_argument("--since-minutes", type=int, default=30)
    args = parser.parse_args()
    
    hosts_fqdn_list = []
    hosts_ip_list = []
    
    # İki yönlü haritalama: Hem IP->Host hem Host->IP
    map_ip_to_host = {}
    map_host_to_ip = {}
    
    username = None
    password = None
    token = None
    
    # 1. Config Dosyasını Oku
    config_paths = ["configuration_file.json", "Datalake_Project/configuration_file.json", "../configuration_file.json"]
    
    for path in config_paths:
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                nb_conf = config.get('Netbackup', {})
                
                ip_str = nb_conf.get('IpAddress', '')
                host_str = nb_conf.get('Hostname', '')
                
                temp_fqdn = []
                temp_ip = []
                
                if host_str: temp_fqdn = [h.strip() for h in host_str.split(',') if h.strip()]
                if ip_str: temp_ip = [i.strip() for i in ip_str.split(',') if i.strip()]
                
                # Varsayılan listeler
                hosts_fqdn_list = temp_fqdn
                hosts_ip_list = temp_ip
                
                # Mapping oluştur
                if temp_fqdn and temp_ip:
                    for i in range(min(len(temp_fqdn), len(temp_ip))):
                        map_host_to_ip[temp_fqdn[i]] = temp_ip[i]
                        map_ip_to_host[temp_ip[i]] = temp_fqdn[i]
                
                username = nb_conf.get('Username') or nb_conf.get('username')
                password = nb_conf.get('Password') or nb_conf.get('password')
                token = nb_conf.get('Bearer_token')
                break 
        except FileNotFoundError: continue
        except Exception: continue
    
    # 2. Command Line Override (NiFi veya Manuel)
    if args.host:
        input_list = [h.strip() for h in args.host.split(',') if h.strip()]
        hosts_fqdn_list = []
        hosts_ip_list = []
        
        for item in input_list:
            # Senaryo 1: Kullanıcı HOSTNAME girdi (Manuel kullanım: --host nbmaster...)
            if item in map_host_to_ip:
                print(f"Mod: Manuel (Hostname Girildi) -> {item}", file=sys.stderr)
                hosts_fqdn_list.append(item)             # Bağlantı için Hostname
                hosts_ip_list.append(map_host_to_ip[item]) # Rapor için Config'deki IP
                
            # Senaryo 2: Kullanıcı/NiFi IP girdi (NiFi kullanımı: --host 10.132...)
            elif item in map_ip_to_host:
                print(f"Mod: NiFi (IP Girildi) -> {item}", file=sys.stderr)
                hosts_fqdn_list.append(map_ip_to_host[item]) # Bağlantı için Config'deki Hostname
                hosts_ip_list.append(item)                   # Rapor için girilen IP
                
            # Senaryo 3: Bilinmeyen değer (Config'de yok)
            else:
                # Basit bir IP regex kontrolü veya varsayım
                is_ip_structure = item.replace('.', '').isdigit() 
                if is_ip_structure:
                    print(f"Bilinmeyen IP: {item}, Hostname olarak da IP kullanılacak.", file=sys.stderr)
                    hosts_fqdn_list.append(item)
                    hosts_ip_list.append(item)
                else:
                    # Hostname girilmiş ama config'de yok, DNS'den IP bulmaya çalış
                    print(f"Bilinmeyen Hostname: {item}, DNS'ten IP çözülecek.", file=sys.stderr)
                    hosts_fqdn_list.append(item)
                    try:
                        resolved_ip = socket.gethostbyname(item)
                        hosts_ip_list.append(resolved_ip)
                    except:
                        hosts_ip_list.append(item)

    if args.username: username = args.username
    if args.password: password = args.password
    if args.token: token = args.token

    if not hosts_fqdn_list:
        print("Hata: İşlenecek host bulunamadı!", file=sys.stderr)
        sys.exit(1)

    all_results = []
    for i, connect_host in enumerate(hosts_fqdn_list):
        try:
            report_ip = hosts_ip_list[i] if i < len(hosts_ip_list) else connect_host
            print(f"Hedef: {connect_host} -> Raporlanacak IP: {report_ip}", file=sys.stderr)
            
            collector = NetBackupDataCollector(
                connect_host=connect_host,
                report_ip=report_ip,
                username=username,
                password=password,
                token=token
            )
            data = collector.collect_all_data(since_minutes=args.since_minutes)
            all_results.extend(data)
        except Exception as e:
            print(f"Hata ({connect_host}): {e}", file=sys.stderr)
            continue
            
    print(json.dumps(all_results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
