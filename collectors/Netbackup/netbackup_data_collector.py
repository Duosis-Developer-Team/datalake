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
        """
        NetBackup collector'ı başlatır
        
        Args:
            host: NetBackup sunucu IP adresi
            username: NetBackup kullanıcı adı (token otomatik alınması için)
            password: NetBackup şifresi (token otomatik alınması için)
            token: Bearer token (opsiyonel, verilmezse otomatik alınır)
            hostname: NetBackup sunucu hostname (SSL certificate için, yoksa DNS'den çözümlenecek)
        """
        self.host = host
        self.username = username
        self.password = password
        self.token = token
        
        # Hostname'i belirle: config'den > DNS lookup > IP fallback
        if hostname:
            self.hostname = hostname
        else:
            try:
                # DNS reverse lookup ile hostname bul
                self.hostname = socket.gethostbyaddr(host)[0]
                print(f"Hostname DNS'den çözümlendi: {self.hostname}", file=sys.stderr)
            except:
                # DNS başarısız, IP'yi kullan
                self.hostname = host
                print(f"Hostname DNS'den çözümlenemedi, IP kullanılıyor: {self.hostname}", file=sys.stderr)
        
        self.base_url = f"https://{host}"
        self.session = requests.Session()
        
        # SSL doğrulamasını tamamen devre dışı bırak
        self.session.verify = False
        
        # SSL hostname doğrulamasını devre dışı bırak
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Custom adapter ile SSL context'i uygula
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
        
        # Token yoksa, username/password ile al
        if not self.token:
            if self.username and self.password:
                print(f"Token bulunamadı, username/password ile token alınıyor...", file=sys.stderr)
                self.token = self.get_auth_token()
                if not self.token:
                    raise Exception("NetBackup authentication başarısız!")
            else:
                raise Exception("Token veya username/password bilgileri gerekli!")
        
        # Session headers'ı güncelle
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*",  # NetBackup API'si için gerekli
            "Host": self.hostname  # Dinamik hostname
        })
    
    def get_auth_token(self) -> str:
        """
        NetBackup API'dan Bearer token al (Zerto mantığı ile)
        
        Returns:
            Bearer token string veya None
        """
        try:
            auth_url = f"{self.base_url}/netbackup/login"
            
            auth_data = {
                "userName": self.username,
                "password": self.password
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": self.hostname  # SSL certificate hostname validation için gerekli
            }
            
            print(f"Authentication URL: {auth_url}", file=sys.stderr)
            print(f"Username: {self.username}", file=sys.stderr)
            print(f"Hostname: {self.hostname}", file=sys.stderr)
            
            response = self.session.post(auth_url, json=auth_data, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            
            token_data = response.json()
            token = token_data.get('token')
            
            if token:
                print(f"NetBackup token başarıyla alındı.", file=sys.stderr)
                return token
            else:
                print(f"Token yanıtında 'token' field'ı bulunamadı: {token_data}", file=sys.stderr)
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"NetBackup token alma hatası: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}", file=sys.stderr)
                print(f"Response text: {e.response.text}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"Token yanıtı JSON parse hatası: {e}", file=sys.stderr)
            return None
        
    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        NetBackup API'ye istek gönderir
        
        Args:
            endpoint: API endpoint'i
            params: Query parametreleri
            
        Returns:
            API yanıtı
            
        Raises:
            requests.RequestException: API isteği başarısız olursa
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API isteği hatası ({endpoint}): {e}", file=sys.stderr)
            raise
    
    def collect_jobs_data(self, since_minutes: Optional[int] = 30) -> Tuple[List[Dict], str]:
        """
        NetBackup jobs verilerini toplar
        
        Args:
            since_minutes: Son kaç dakikadaki veriler (None = tümü). Varsayılan: 30
            
        Returns:
            (jobs_list, server_timestamp)
        """
        try:
            endpoint = "/netbackup/admin/jobs"
            params = {}
            
            # Zaman filtresi ekle
            if since_minutes is not None:
                now = datetime.now(timezone.utc)
                time_limit = now - timedelta(minutes=since_minutes)
                time_limit_iso = time_limit.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                params["filter"] = f"lastUpdateTime gt {time_limit_iso}"
                params["page[limit]"] = "999"
                params["sort"] = "-lastUpdateTime"
            
            jobs_data = self.make_request(endpoint, params)
            jobs_list = []
            
            # Pagination desteği
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
            
            # Jobs verilerini işle
            for job in all_jobs:
                attrs = job.get("attributes", {})
                job_data = {
                    'id': job.get("id"),
                    'type': job.get("type"),
                    'jobId': attrs.get("jobId"),
                    'parentJobId': attrs.get("parentJobId"),
                    'activeProcessId': attrs.get("activeProcessId"),
                    'jobType': attrs.get("jobType"),
                    'jobSubType': attrs.get("jobSubType"),
                    'policyType': attrs.get("policyType"),
                    'policyName': attrs.get("policyName"),
                    'scheduleType': attrs.get("scheduleType"),
                    'scheduleName': attrs.get("scheduleName"),
                    'clientName': attrs.get("clientName"),
                    'jobOwner': attrs.get("jobOwner"),
                    'jobGroup': attrs.get("jobGroup"),
                    'backupId': attrs.get("backupId"),
                    'destinationStorageUnitName': attrs.get("destinationStorageUnitName"),
                    'destinationMediaServerName': attrs.get("destinationMediaServerName"),
                    'dataMovement': attrs.get("dataMovement"),
                    'streamNumber': attrs.get("streamNumber"),
                    'copyNumber': attrs.get("copyNumber"),
                    'priority': attrs.get("priority"),
                    'compression': attrs.get("compression"),
                    'state': attrs.get("state"),
                    'numberOfFiles': attrs.get("numberOfFiles"),
                    'estimatedFiles': attrs.get("estimatedFiles"),
                    'kilobytesTransferred': attrs.get("kilobytesTransferred"),
                    'kilobytesToTransfer': attrs.get("kilobytesToTransfer"),
                    'transferRate': attrs.get("transferRate"),
                    'percentComplete': attrs.get("percentComplete"),
                    'restartable': bool(attrs.get("restartable", 0)),
                    'suspendable': bool(attrs.get("suspendable", 0)),
                    'resumable': bool(attrs.get("resumable", 0)),
                    'frozenImage': bool(attrs.get("frozenImage", 0)),
                    'transportType': attrs.get("transportType"),
                    'currentOperation': attrs.get("currentOperation"),
                    'sessionId': attrs.get("sessionId"),
                    'numberOfTapeToEject': attrs.get("numberOfTapeToEject"),
                    'submissionType': attrs.get("submissionType"),
                    'auditDomainType': attrs.get("auditDomainType"),
                    'startTime': attrs.get("startTime"),
                    'endTime': attrs.get("endTime"),
                    'activeTryStartTime': attrs.get("activeTryStartTime"),
                    'lastUpdateTime': attrs.get("lastUpdateTime"),
                    'childCount': attrs.get("childCount"),
                    'jobPath': attrs.get("jobPath"),
                    'retentionLevel': attrs.get("retentionLevel"),
                    'try': attrs.get("try"),
                    'cancellable': bool(attrs.get("cancellable", 0)),
                    'jobQueueReason': attrs.get("jobQueueReason"),
                    'kilobytesDataTransferred': attrs.get("kilobytesDataTransferred"),
                    'elapsedTime': attrs.get("elapsedTime"),
                    'activeElapsedTime': attrs.get("activeElapsedTime"),
                    'dteMode': attrs.get("dteMode"),
                    'workloadDisplayName': attrs.get("workloadDisplayName"),
                    'offHostType': attrs.get("offHostType"),
                    'dedupRatio': attrs.get("dedupRatio"),
                    'status': attrs.get("status"),
                    'profileName': attrs.get("profileName"),
                    'dedupSpaceRatio': attrs.get("dedupSpaceRatio"),
                    'compressionSpaceRatio': attrs.get("compressionSpaceRatio"),
                    'acceleratorOptimization': attrs.get("acceleratoroptimization"),
                    'assetId': attrs.get("assetid"),
                    'destinationMediaId': attrs.get("destinationmediaid"),
                    'dumpHost': attrs.get("dumphost"),
                    'instanceDatabaseName': attrs.get("instancedatabasename"),
                    'qReasonCode': attrs.get("qreasoncode"),
                    'qResource': attrs.get("qresource"),
                    'restoreBackupIds': attrs.get("restorebackupids"),
                    'robotName': attrs.get("robotname"),
                    'vaultName': attrs.get("vaultname")
                }
                jobs_list.append(job_data)
            
            # Server timestamp'i al
            server_timestamp = datetime.now(timezone.utc).isoformat()
            
            return jobs_list, server_timestamp
            
        except Exception as e:
            print(f"Jobs veri toplama hatası: {e}", file=sys.stderr)
            return [], datetime.now(timezone.utc).isoformat()
    
    def collect_disk_pools_data(self) -> Tuple[List[Dict], str]:
        """
        NetBackup disk pools verilerini toplar
        
        Returns:
            (disk_pools_list, server_timestamp)
        """
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
                    'sType': attrs.get("sType"),
                    'storageCategory': attrs.get("storageCategory"),
                    'diskVolumes_name': disk_volumes.get("name"),
                    'diskVolumes_id': disk_volumes.get("id"),
                    'diskVolumes_diskMediaId': disk_volumes.get("diskMediaId"),
                    'diskVolumes_state': disk_volumes.get("state"),
                    'diskVolumes_rawSizeBytes': disk_volumes.get("rawSizeBytes"),
                    'diskVolumes_freeSizeBytes': disk_volumes.get("freeSizeBytes"),
                    'diskVolumes_isReplicationSource': bool(disk_volumes.get("isReplicationSource", False)),
                    'diskVolumes_isReplicationTarget': bool(disk_volumes.get("isReplicationTarget", False)),
                    'diskVolumes_wormIndelibleMinimumInterval': disk_volumes.get("wormIndelibleMinimumInterval"),
                    'diskVolumes_wormIndelibleMaximumInterval': disk_volumes.get("wormIndelibleMaximumInterval"),
                    'highWaterMark': attrs.get("highWaterMark"),
                    'lowWaterMark': attrs.get("lowWaterMark"),
                    'max_limitIoStreams': int(attrs.get("maximumIoStreams", {}).get("limitIoStreams", 0)),
                    'diskPoolState': attrs.get("diskPoolState"),
                    'rawSizeBytes': attrs.get("rawSizeBytes"),
                    'usableSizeBytes': attrs.get("usableSizeBytes"),
                    'availableSpaceBytes': attrs.get("availableSpaceBytes"),
                    'usedCapacityBytes': attrs.get("usedCapacityBytes"),
                    'wormCapable': bool(attrs.get("wormCapable", False)),
                    'readOnly': bool(attrs.get("readOnly", False)),
                    'mediaServersCount': attrs.get("mediaServersCount")
                }
                disk_pools_list.append(disk_pool_data)
            
            # Server timestamp'i al
            server_timestamp = datetime.now(timezone.utc).isoformat()
            
            return disk_pools_list, server_timestamp
            
        except Exception as e:
            print(f"Disk pools veri toplama hatası: {e}", file=sys.stderr)
            return [], datetime.now(timezone.utc).isoformat()
    
    def generate_unique_timestamp(self, entity_id: str, api_timestamp: Optional[str] = None) -> str:
        """
        Entity ID'sine göre benzersiz timestamp oluşturur
        
        Args:
            entity_id: Entity ID'si
            api_timestamp: API'den gelen timestamp (opsiyonel)
            
        Returns:
            Benzersiz timestamp string
        """
        # Önce API timestamp'i kullan
        if api_timestamp:
            try:
                base_timestamp = datetime.fromisoformat(api_timestamp.replace('Z', '+00:00'))
            except:
                base_timestamp = datetime.now(timezone.utc)
        else:
            base_timestamp = datetime.now(timezone.utc)
        
        # Entity ID'sine göre microsecond offset hesapla
        entity_hash = hash(entity_id) % 1000000
        unique_timestamp = base_timestamp.replace(microsecond=entity_hash)
        
        return unique_timestamp.isoformat()
    
    def collect_all_data(self, since_minutes: Optional[int] = 30) -> List[Dict]:
        """
        Tüm NetBackup verilerini toplar ve JSON formatında döndürür
        
        Args:
            since_minutes: Son kaç dakikadaki veriler (None = tümü). Varsayılan: 30
            
        Returns:
            JSON formatında veri listesi
        """
        print("NetBackup veri toplama başlatılıyor...", file=sys.stderr)
        
        all_data = []
        
        # Jobs verilerini topla
        try:
            jobs_data, jobs_timestamp = self.collect_jobs_data(since_minutes)
            print(f"Jobs verisi toplandı: {len(jobs_data)} kayıt", file=sys.stderr)
            
            for job in jobs_data:
                # Benzersiz timestamp oluştur
                entity_id = job.get('id') or job.get('jobId') or f"job-{job.get('jobId', 'unknown')}"
                api_timestamp = job.get('lastUpdateTime')
                unique_timestamp = self.generate_unique_timestamp(entity_id, api_timestamp)
                
                record = {
                    'data_type': 'netbackup_job',
                    'collection_timestamp': unique_timestamp,
                    'netbackup_host': self.host,
                    **job
                }
                all_data.append(record)
                
        except Exception as e:
            print(f"Jobs veri toplama hatası: {e}", file=sys.stderr)
        
        # Disk pools verilerini topla
        try:
            disk_pools_data, pools_timestamp = self.collect_disk_pools_data()
            print(f"Disk pools verisi toplandı: {len(disk_pools_data)} kayıt", file=sys.stderr)
            
            for pool in disk_pools_data:
                # Benzersiz timestamp oluştur
                entity_id = pool.get('id') or pool.get('name') or f"pool-{pool.get('name', 'unknown')}"
                unique_timestamp = self.generate_unique_timestamp(entity_id)
                
                record = {
                    'data_type': 'netbackup_disk_pool',
                    'collection_timestamp': unique_timestamp,
                    'netbackup_host': self.host,
                    **pool
                }
                all_data.append(record)
                
        except Exception as e:
            print(f"Disk pools veri toplama hatası: {e}", file=sys.stderr)
        
        print(f"Toplam {len(all_data)} kayıt toplandı", file=sys.stderr)
        return all_data

def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description="NetBackup veri toplayıcı")
    parser.add_argument("--host", type=str, help="NetBackup sunucu IP adresi")
    parser.add_argument("--hostname", type=str, help="NetBackup sunucu hostname")
    parser.add_argument("--username", type=str, help="NetBackup kullanıcı adı")
    parser.add_argument("--password", type=str, help="NetBackup şifresi")
    parser.add_argument("--token", type=str, help="NetBackup Bearer token (opsiyonel)")
    parser.add_argument("--hosts", type=str, help="Virgülle ayrılmış host listesi")
    parser.add_argument("--config-file", type=str, help="JSON config dosyası yolu")
    parser.add_argument("--since-minutes", type=int, default=30, help="Son kaç dakikadaki veriler (None = tümü)")
    
    args = parser.parse_args()
    
    hosts_to_process = []
    hostnames = []
    username = None
    password = None
    token = None
    
    # 1. Öncelik: Command-line arguments
    if args.host and args.username and args.password:
        # NiFi argument'larından username/password ile al
        hosts_to_process = [args.host]
        username = args.username
        password = args.password
        token = args.token  # Opsiyonel
        
        # Hostname argument'tan gelmediyse, config'den eşleşen hostname'i bul
        if args.hostname:
            hostnames = [args.hostname]
            print(f"Command-line argument'larından alındı: Host={args.host}, Hostname={args.hostname}, Username={username}", file=sys.stderr)
        else:
            # Config dosyasından hostname eşleştirmesi yap
            matched_hostname = None
            try:
                config_paths = [
                    "configuration_file.json",
                    "Datalake_Project/configuration_file.json",
                    "../Datalake_Project/configuration_file.json",
                    "./Datalake_Project/configuration_file.json",
                    "/Datalake_Project/configuration_file.json"
                ]
                
                for config_path in config_paths:
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            netbackup_config = config.get('Netbackup', {})
                            ip_addresses = netbackup_config.get('IpAddress', '')
                            hostname_config = netbackup_config.get('Hostname', '')
                            
                            if ip_addresses and hostname_config:
                                ips = [ip.strip() for ip in ip_addresses.split(',')]
                                hostnames_list = [hn.strip() for hn in hostname_config.split(',')]
                                
                                # IP'yi bul ve eşleşen hostname'i al
                                if args.host in ips:
                                    idx = ips.index(args.host)
                                    if idx < len(hostnames_list):
                                        matched_hostname = hostnames_list[idx]
                                        print(f"Config dosyasından hostname eşleştirildi: {args.host} -> {matched_hostname}", file=sys.stderr)
                                        break
                    except FileNotFoundError:
                        continue
                    except Exception:
                        continue
            except Exception:
                pass
            
            hostnames = [matched_hostname] if matched_hostname else [args.host]
            hostname_source = "Config'den" if matched_hostname else "Yok (DNS kullanılacak)"
            print(f"Command-line argument'larından alındı: Host={args.host}, Hostname={hostname_source}, Username={username}", file=sys.stderr)
            
    elif args.host and args.token:
        # Backward compatibility: Token ile direkt
        hosts_to_process = [args.host]
        username = None
        password = None
        token = args.token
        
        # Hostname argument'tan gelmediyse, config'den eşleşen hostname'i bul
        if args.hostname:
            hostnames = [args.hostname]
        else:
            # Config dosyasından hostname eşleştirmesi yap (aynı mantık)
            matched_hostname = None
            try:
                config_paths = [
                    "configuration_file.json",
                    "Datalake_Project/configuration_file.json",
                    "../Datalake_Project/configuration_file.json",
                    "./Datalake_Project/configuration_file.json",
                    "/Datalake_Project/configuration_file.json"
                ]
                
                for config_path in config_paths:
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            netbackup_config = config.get('Netbackup', {})
                            ip_addresses = netbackup_config.get('IpAddress', '')
                            hostname_config = netbackup_config.get('Hostname', '')
                            
                            if ip_addresses and hostname_config:
                                ips = [ip.strip() for ip in ip_addresses.split(',')]
                                hostnames_list = [hn.strip() for hn in hostname_config.split(',')]
                                
                                if args.host in ips:
                                    idx = ips.index(args.host)
                                    if idx < len(hostnames_list):
                                        matched_hostname = hostnames_list[idx]
                                        break
                    except FileNotFoundError:
                        continue
                    except Exception:
                        continue
            except Exception:
                pass
            
            hostnames = [matched_hostname] if matched_hostname else [args.host]
        
        print(f"Command-line argument'larından alındı (token): Host={args.host}, Token={token[:20]}...", file=sys.stderr)
    else:
        # 2. Fallback: Config dosyasından oku
        print(f"Config dosyasından bilgiler okunuyor...", file=sys.stderr)
        try:
            # Datalake_Project klasöründe ara
            config_paths = [
                "configuration_file.json",
                "Datalake_Project/configuration_file.json",
                "../Datalake_Project/configuration_file.json",
                "./Datalake_Project/configuration_file.json",
                "/Datalake_Project/configuration_file.json"
            ]
            
            config_loaded = False
            for config_path in config_paths:
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        netbackup_config = config.get('Netbackup', {})
                        ip_addresses = netbackup_config.get('IpAddress', '')
                        
                        if ip_addresses:
                            hosts_to_process = [host.strip() for host in ip_addresses.split(',')]
                            # Hostname'i config'den al, yoksa IP'yi kullan
                            hostname_config = netbackup_config.get('Hostname', '')
                            if hostname_config:
                                hostnames = [hostname.strip() for hostname in hostname_config.split(',')]
                            else:
                                hostnames = hosts_to_process  # Fallback: IP'leri hostname olarak kullan
                        
                        # Username/Password oku (case-insensitive)
                        username = netbackup_config.get('Username') or netbackup_config.get('username')
                        password = netbackup_config.get('Password') or netbackup_config.get('password')
                        
                        # Backward compatibility: Bearer_token varsa al
                        token = netbackup_config.get('Bearer_token') or netbackup_config.get('bearer_token')
                        
                    print(f"Config dosyasından alındı ({config_path}): Hosts={hosts_to_process}, Username={username}, Token={'Var' if token else 'Yok'}", file=sys.stderr)
                    config_loaded = True
                    break
                except FileNotFoundError:
                    continue
                except Exception as e:
                    print(f"Config dosyası okuma hatası ({config_path}): {e}", file=sys.stderr)
                    continue
            
            if not config_loaded:
                raise FileNotFoundError("configuration_file.json dosyası hiçbir konumda bulunamadı")
                
        except Exception as e:
            print(f"Config dosyası okuma hatası: {e}", file=sys.stderr)
            print("Hata: Ne argument'lardan ne de config dosyasından bilgi alınamadı!", file=sys.stderr)
            sys.exit(1)
    
    # Validation: Token veya username/password gerekli
    if not token and not (username and password):
        print("Hata: Token veya username/password bilgileri gerekli!", file=sys.stderr)
        sys.exit(1)
    
    if not hosts_to_process:
        print("Hata: Host bilgisi gerekli!", file=sys.stderr)
        sys.exit(1)
    
    # Her host için veri topla
    all_results = []
    for i, host in enumerate(hosts_to_process):
        try:
            # Hostname'i al (opsiyonel)
            hostname = hostnames[i] if i < len(hostnames) and hostnames[i] != host else None
            if hostname:
                print(f"Host {host} (hostname: {hostname}) için veri toplanıyor...", file=sys.stderr)
            else:
                print(f"Host {host} için veri toplanıyor (hostname DNS'den çözümlenecek)...", file=sys.stderr)
            
            # Collector'ı oluştur (username/password veya token ile)
            collector = NetBackupDataCollector(
                host=host,
                username=username,
                password=password,
                token=token,
                hostname=hostname
            )
            
            host_data = collector.collect_all_data(args.since_minutes)
            all_results.extend(host_data)
        except Exception as e:
            print(f"Host {host} için veri toplama hatası: {e}", file=sys.stderr)
            continue
    
    # JSON çıktısını stdout'a yazdır
    try:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"JSON çıktı hatası: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
