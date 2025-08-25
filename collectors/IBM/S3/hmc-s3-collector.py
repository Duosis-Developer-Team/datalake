#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HMC Veri Toplama Betiği (HMC Data Collector Script)

Bu betik, bir IBM Power Systems HMC (Hardware Management Console) arayüzüne
REST API üzerinden bağlanarak yönetilen sistemler, LPAR'lar ve VIOS'lar hakkında
envanter ve performans metriklerini toplar.

Toplanan veriler, her bir kaydın türünü belirten bir "data_type" anahtarı ile
etiketlenir ve tek bir JSON dizisi olarak standart çıktıya (stdout) basılır.
Bu çıktı, Apache NiFi gibi bir orkestrasyon aracı tarafından işlenmek üzere
tasarlanmıştır.

Kullanım:
    python3 hmc_collector.py --host <HMC_IP_ADRESI> --username <KULLANICI_ADI> --password <SIFRE>

Gereksinimler:
    - requests

SSL Doğrulama Uyarısı:
Mevcut HMC ortamlarında genellikle kendinden imzalı (self-signed) sertifikalar
kullanıldığından, SSL sertifika doğrulaması devre dışı bırakılmıştır (`verify=False`).
Bu, üretim ortamları için güvenlik riski oluşturabilir.
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests
# SSL uyarılarını bastırmak için
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# --- Yardımcı Fonksiyonlar ---

def log_message(message):
    """Mesajları standart hataya (stderr) yazar, böylece stdout'taki JSON'u bozmaz."""
    print(f"[{datetime.now().isoformat()}] {message}", file=sys.stderr)

def flatten_dict(d, parent_key='', sep='_'):
    """İç içe bir sözlüğü düzleştirir. Örn: {'a': {'b': 1}} -> {'a_b': 1}"""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        # HMC'den gelen [deger, min, max] formatındaki listeleri sadeleştir
        elif isinstance(v, list) and len(v) == 3:
            items.append((new_key, v[0]))
        else:
            items.append((new_key, v))
    return dict(items)


# --- API Etkileşim Fonksiyonları ---

def login_to_hmc(host, username, password):
    """
    HMC'ye oturum açar ve sonraki istekler için bir session nesnesi döndürür.
    """
    log_message(f"HMC'ye bağlanılıyor: {host}")
    login_url = f"https://{host}:443/rest/api/web/Logon"
    
    # login.xml dosyasındaki gibi bir XML gövdesi oluştur
    login_xml = f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <LogonRequest xmlns="http://www.ibm.com/xmlns/systems/power/firmware/web/mc/2012_10/" schemaVersion="V1_0">
      <UserID>{username}</UserID>
      <Password>{password}</Password>
    </LogonRequest>
    """
    
    headers = {
        'Content-Type': 'application/vnd.ibm.powervm.web+xml; type=LogonRequest',
        'Accept': 'application/vnd.ibm.powervm.web+xml; type=LogonResponse',
    }
    
    try:
        session = requests.Session()
        response = session.put(
            login_url,
            data=login_xml.encode('utf-8'),
            headers=headers,
            verify=False,  # SSL doğrulaması kapalı
            timeout=30
        )
        
        response.raise_for_status()  # HTTP 4xx/5xx hataları için exception fırlatır
        log_message("HMC bağlantısı başarılı.")
        return session
        
    except requests.exceptions.RequestException as e:
        log_message(f"HATA: HMC bağlantısı başarısız: {e}")
        return None

def fetch_metric_from_href(session, href):
    """Verilen bir href linkinden JSON metrik verisini çeker."""
    try:
        response = session.get(href, verify=False, timeout=60, headers={'Accept': 'application/json'})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log_message(f"HATA: Metrik linki çekilemedi ({href}): {e}")
        return None
    except json.JSONDecodeError:
        log_message(f"HATA: Geçersiz JSON yanıtı alındı: {href}")
        return None

def get_managed_systems(session, host):
    """HMC tarafından yönetilen tüm sistemlerin UUID'lerini döndürür."""
    log_message("Yönetilen sistemler (Managed Systems) alınıyor...")
    url = f"https://{host}:12443/rest/api/uom/ManagedSystem"
    try:
        response = session.get(url, verify=False, timeout=30, headers={'Accept': 'application/atom+xml'})
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        
        system_uuids = []
        # XML içindeki her 'entry'yi (her bir ManagedSystem) işle
        for entry in root.findall('atom:entry', namespaces):
            content = entry.find('atom:content', namespaces)
            if content is not None:
                ms = content.find('{http://www.ibm.com/xmlns/systems/power/firmware/uom/2012_10/}ManagedSystem')
                if ms is not None:
                    uuid = ms.find('{http://www.ibm.com/xmlns/systems/power/firmware/uom/2012_10/}SystemFirmware/../Metadata/Atom/AtomID').text
                    system_uuids.append(uuid)
        
        log_message(f"{len(system_uuids)} adet yönetilen sistem bulundu.")
        return system_uuids

    except requests.exceptions.RequestException as e:
        log_message(f"HATA: Yönetilen sistemler alınamadı: {e}")
        return []
    except ET.ParseError as e:
        log_message(f"HATA: Yönetilen sistem XML'i işlenemedi: {e}")
        return []


# --- Ana Veri Çekme ve İşleme Mantığı ---

def process_and_collect_metrics(session, host, system_uuid):
    """
    Belirli bir yönetilen sistem için Aggregated ve VIOS metriklerini toplar ve işler.
    """
    collected_data = []
    log_message(f"[{system_uuid}] için metrik toplama işlemi başlatıldı.")
    
    # 5 dakika öncesi ve şimdiki zamanı UTC olarak al
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=5)
    start_ts = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_ts = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    # 1. Aggregated (LPAR) Metrikleri Toplama
    # Bu bölüm, PHP kodundaki fetchAggregatedMetrics ve downloadHrefData adımlarını birleştirir.
    # Önce LPAR listesini almamız gerekiyor (bu örnekte basitleştirilmiştir)
    # Gerçek bir senaryoda, önce /ManagedSystem/{uuid}/LogicalPartition listesi çekilir.
    # Bu örnek, doğrudan AggregatedMetrics endpoint'ine gider.
    
    agg_metrics_url = f"https://{host}:12443/rest/api/pcm/ManagedSystem/{system_uuid}/AggregatedMetrics?StartTS={start_ts}&EndTS={end_ts}"
    
    log_message(f"[{system_uuid}] Aggregated (LPAR) metrikleri alınıyor...")
    try:
        response = session.get(agg_metrics_url, verify=False, timeout=60, headers={'Accept': 'application/atom+xml'})
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        metric_hrefs = [link.get('href') for link in root.findall(".//atom:link[@rel='related']", namespaces)]
        
        for href in metric_hrefs:
            metric_data = fetch_metric_from_href(session, href)
            if metric_data:
                # Gelen veriyi işle ve düzleştir
                util_samples = metric_data.get("systemUtil", {}).get("utilSamples", [])
                for sample in util_samples:
                    sample_timestamp = sample.get("sampleInfo", {}).get("timeStamp")
                    # LPAR verilerini işle
                    for lpar_util in sample.get("lparsUtil", []):
                        flat_lpar = flatten_dict(lpar_util)
                        flat_lpar['data_type'] = 'metric_lpar'
                        flat_lpar['managed_system_uuid'] = system_uuid
                        flat_lpar['collection_timestamp'] = sample_timestamp
                        collected_data.append(flat_lpar)
                    # VIOS verilerini işle
                    for vios_util in sample.get("viosUtil", []):
                        flat_vios = flatten_dict(vios_util)
                        flat_vios['data_type'] = 'metric_vios'
                        flat_vios['managed_system_uuid'] = system_uuid
                        flat_vios['collection_timestamp'] = sample_timestamp
                        collected_data.append(flat_vios)

    except Exception as e:
        log_message(f"HATA: [{system_uuid}] Aggregated metrikleri işlenirken hata oluştu: {e}")

    # Not: Gerçek bir senaryoda, VIOS envanter ve diğer envanter (disk, network, etc.)
    # verileri için ayrı endpoint'lere de gidilmesi gerekir. Bu betik, ana metrik
    # akışına odaklanmıştır.
    
    return collected_data


# --- Betiğin Ana Giriş Noktası ---

def main():
    """Betiğin ana orkestrasyon fonksiyonu."""
    
    parser = argparse.ArgumentParser(description="IBM HMC Veri Toplama Betiği")
    parser.add_argument("--host", required=True, help="HMC sunucusunun IP adresi veya FQDN'i")
    parser.add_argument("--username", required=True, help="HMC kullanıcı adı")
    parser.add_argument("--password", required=True, help="HMC şifresi")
    args = parser.parse_args()

    # 1. HMC'ye giriş yap
    session = login_to_hmc(args.host, args.username, args.password)
    if not session:
        sys.exit(1) # Bağlantı hatası durumunda çık

    # 2. Yönetilen sistemleri al
    system_uuids = get_managed_systems(session, args.host)
    if not system_uuids:
        log_message("Hiç yönetilen sistem bulunamadı veya alınamadı. Çıkılıyor.")
        sys.exit(0)

    # 3. Tüm verileri toplayacak ana liste
    all_collected_data = []

    # 4. Her bir sistem için metrikleri topla
    for uuid in system_uuids:
        system_data = process_and_collect_metrics(session, args.host, uuid)
        all_collected_data.extend(system_data)

    # 5. Toplanan tüm veriyi JSON formatında standart çıktıya bas
    if all_collected_data:
        print(json.dumps(all_collected_data, indent=2))
        log_message(f"Toplam {len(all_collected_data)} adet metrik kaydı başarıyla toplandı ve yazdırıldı.")
    else:
        log_message("Toplanacak hiç metrik bulunamadı.")


if __name__ == "__main__":
    main()