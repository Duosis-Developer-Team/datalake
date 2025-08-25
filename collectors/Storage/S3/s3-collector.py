# -*- coding: utf-8 -*-
import requests
import json
import os
import sys
import argparse
from requests.auth import HTTPBasicAuth
import urllib3
from datetime import datetime, timezone

# --- AYARLAR VE SABİTLER ---
# Bu betik, IBM S3ICOS sisteminden veri toplar ve bu veriyi mantıksal gruplara
# ayırarak (envanter, kasa metrikleri, havuz metrikleri) her biri için ayrı 'data_type'
# ile etiketlenmiş bir JSON listesi olarak standart çıktıya (stdout) yazar.

# --- YARDIMCI SINIF: S3ICOS API İstemcisi ---
class S3icosClient:
    """
    IBM S3ICOS API ile iletişimi yöneten sınıf.
    """
    def __init__(self, host, username, password, verify_ssl=False):
        self.base_url = f"https://{host}"
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.verify = verify_ssl
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def get_data(self, endpoint):
        """
        Belirtilen endpoint'e kimliği doğrulanmış bir GET isteği gönderir
        ve JSON verisini döndürür.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            print(f"INFO: Veri çekiliyor: {url}", file=sys.stderr)
            response = self.session.get(url, auth=self.auth, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"HATA: API isteği başarısız oldu {url}: {e}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"HATA: JSON verisi ayrıştırılamadı {url}", file=sys.stderr)
        return None

# --- VERİ PARÇALAMA VE OLUŞTURMA FONKSİYONLARI ---

def create_vault_inventory_record(vault, base_info):
    """Vault'un envanter/konfigürasyon verisinden bir kayıt oluşturur."""
    return {
        **base_info,
        "data_type": "s3icos_vault_inventory",
        "uuid": vault.get("uuid"),
        "description": vault.get("description"),
        "type": vault.get("type"),
        "width": vault.get("width"),
        "threshold": vault.get("threshold"),
        "write_threshold": vault.get("writeThreshold"),
        "privacy_enabled": vault.get("privacyEnabled"),
        "vault_purpose": vault.get("vaultPurpose"),
        "soft_quota_bytes": vault.get("softQuota"),
        "hard_quota_bytes": vault.get("hardQuota")
    }

def create_vault_metrics_record(vault, base_info):
    """Vault'un anlık metriklerinden bir kayıt oluşturur."""
    return {
        **base_info,
        "data_type": "s3icos_vault_metrics",
        "allotted_size_bytes": vault.get("allottedSize"),
        "usable_size_bytes": vault.get("usableSize"),
        "used_physical_size_bytes": vault.get("usedPhysicalSizeFromStorage"),
        "used_logical_size_bytes": vault.get("usedLogicalSizeFromStorage"),
        "object_count_estimate": vault.get("estimateObjectCount"),
        "allotment_usage": vault.get("allotmentUsage"),
        # YENİ EKLENDİ
        "estimate_usable_used_logical_size_bytes": vault.get("estimateUsableUsedLogicalSizeFromStorage"),
        "estimate_usable_total_logical_size_bytes": vault.get("estimateUsableTotalLogicalSizeFromStorage")
    }

def create_pool_metrics_records(vault, base_info):
    """Bir vault'a bağlı depolama havuzlarının metriklerinden kayıtlar oluşturur."""
    records = []
    storage_pools = vault.get("storagePools", [])
    if not isinstance(storage_pools, list):
        return []

    for pool_data in storage_pools:
        pool = pool_data.get("storagePool", {})
        if not pool:
            continue
        
        record = {
            **base_info,
            "data_type": "s3icos_pool_metrics",
            "pool_id": pool.get("id"),
            "pool_name": pool.get("name"),
            "usable_size_bytes": pool.get("usableSize"),
            "used_physical_size_bytes": pool.get("usedPhysicalSizeFromStorage"),
            "used_logical_size_bytes": pool.get("usedLogicalSizeFromStorage"),
            # YENİ EKLENDİ
            "estimate_usable_used_logical_size_bytes": pool.get("estimateUsableUsedLogicalSizeFromStorage"),
            "estimate_usable_total_logical_size_bytes": pool.get("estimateUsableTotalLogicalSizeFromStorage")
        }
        records.append(record)
    return records


# --- ANA İŞ AKIŞI ---

def main():
    """Tüm veri işleme adımlarını sırayla yürüten ana fonksiyon."""
    parser = argparse.ArgumentParser(description="IBM S3ICOS için veri toplama ve gruplandırma betiği.")
    parser.add_argument('--host', required=True, help="S3ICOS IP adresi veya FQDN.")
    parser.add_argument('--username', required=True, help="S3ICOS kullanıcı adı.")
    parser.add_argument('--password', required=True, help="S3ICOS şifresi.")
    args = parser.parse_args()

    client = S3icosClient(args.host, args.username, args.password)
    api_data = client.get_data('/manager/api/json/1.0/listVaults.adm')
    if not api_data:
        sys.exit(1)

    all_vaults = api_data.get('responseData', {}).get('vaults', [])
    if not all_vaults:
        print("UYARI: API yanıtında 'vaults' verisi bulunamadı.", file=sys.stderr)
        return

    all_records = []
    collection_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

    for vault in all_vaults:
        if not isinstance(vault, dict) or 'id' not in vault:
            continue
            
        base_info = {
            "collection_timestamp": collection_timestamp,
            "vault_id": vault.get("id"),
            "vault_name": vault.get("name")
        }
        
        all_records.append(create_vault_inventory_record(vault, base_info))
        all_records.append(create_vault_metrics_record(vault, base_info))
        all_records.extend(create_pool_metrics_records(vault, base_info))

    print(f"INFO: {len(all_vaults)} adet vault'tan toplam {len(all_records)} kayıt oluşturuldu.", file=sys.stderr)
    
    try:
        json.dump(all_records, sys.stdout, indent=4)
        print(f"\nINFO: Veri başarıyla standart çıktıya yazdırıldı.", file=sys.stderr)
    except Exception as e:
        print(f"HATA: Sonuç standart çıktıya yazdırılırken hata oluştu: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
