#!/usr/bin/env python3
# pysvc_iostats.py
#
# 1) SVC JSON toplama (işlenmiş + _response ham çıktılar)
#    (Bu sürümde çıktılar stdout'a JSON olarak basılır, dosyalara yazılmaz)
# 2) En güncel I/O-stat dump’larını indirme (Bu akışta işlenmez, ayrı bir NiFi akışı gerektirir)
# 3) Dump’ları organize edip delta XML üretme (Bu akışta işlenmez, ayrı bir NiFi akışı gerektirir)
#
# Python ≥3.9 önerilir.

import argparse
import json
import os
import re
import sys
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from typing import Dict, List, Tuple, Optional

# ---------------------------------------------------------------------------
# DİZİN SABİTLERİ (Bu flow için doğrudan kullanılmaz, ancak kodda kalabilir)
# ---------------------------------------------------------------------------
JSON_BASE_DIR = "./pysvc_unified_outputs"
IOSTAT_BASE_DIR = "/nifiScripts_old/IBM/IBM_Storage/iostats"
DELTA_BASE_DIR = "/nifiScripts_old/IBM/IBM_Storage/pysvc_unified_outputs"

# ---------------------------------------------------------------------------
# 0) ARGÜMANLAR
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Komut satırı argümanlarını ayrıştırır."""
    p = argparse.ArgumentParser(
        description="SVC I/O-stat boru hattı (IP listesi zorunludur)")

    p.add_argument(
        "-c", "--config", default="config.json",
        help="Config JSON yolu (vars: config.json)")
    p.add_argument(
        "-H", "--hosts", required=False,  # `required=False` olarak değiştirildi
        help="Virgül/boşlukla ayrılmış IP listesi "
             "(örn. 10.3.2.10,10.3.2.11 10.3.2.12)")

    p.add_argument("-u", "--username",
                    help="SVC CLI kullanıcı adı (config’i ezer)")
    p.add_argument("-p", "--password",
                    help="SVC CLI parolası (config’i ezer)")
    
    return p.parse_args()

# ---------------------------------------------------------------------------
# 1) CONFIG + ARGÜMANDAN HOST DİZİSİ
# ---------------------------------------------------------------------------
def load_systems(config_path: str,
                 hosts_arg: str,
                 username: Optional[str],
                 password: Optional[str]) -> List[Dict]:
    """
    Yapılandırma dosyasından sistem bilgilerini yükler ve komut satırı
    argümanları ile birleştirir.
    """
    try:
        # configuration_file.json dosyasını okuyun
        with open("/Datalake_Project/configuration_file.json", "r", encoding="utf-8") as f:
            full_config = json.load(f)

        # Sadece IBM-Virtualize bölümünü alın
        virtualize_cfg = full_config.get("IBM-Virtualize", {})

    except (FileNotFoundError, KeyError) as exc:
        # Hata durumunda loglama ve çıkış
        print(f"[CONFIG HATASI] {exc}", file=sys.stderr)
        sys.exit(1)

    # -H argümanı verilmezse, host değerini doğrudan config dosyasından alın
    if not hosts_arg and "host" in virtualize_cfg:
        hosts_arg = virtualize_cfg["host"]

    # Virgül veya boşlukla ayrılmış hostları listeye dönüştür
    hosts = [h.strip() for h in re.split(r"[,\s]+", hosts_arg) if h.strip()]
    if not hosts:
        print("[ARG] -H/--hosts ile en az bir IP girmelisiniz.", file=sys.stderr)
        sys.exit(1)

    # config dosyasındaki değerleri varsayılan olarak kullanın
    common = {
        "username": virtualize_cfg.get("username"),
        "password": virtualize_cfg.get("password"),
        "port": virtualize_cfg.get("port", 22),
        "remote_path": virtualize_cfg.get("remote_path"),
        "local_path": virtualize_cfg.get("local_path"),
    }

    # ----- CLI argümanları config üzerine yazar (mevcut mantığı koruyun) -----
    if username is not None:
        common["username"] = username
    if password is not None:
        common["password"] = password
    # -------------------------------------------------------------------------

    # Her host için ayrı bir yapılandırma sözlüğü oluştur
    return [{**common, "host": h} for h in hosts]

# ---------------------------------------------------------------------------
# 2) SVC → JSON (stdout'a basılır)
# ---------------------------------------------------------------------------
def svc_json_dump(svc_cfg: dict) -> List[Dict]:
    """
    Belirtilen SVC sisteminden JSON verilerini toplar ve bir liste olarak döndürür.
    Her kayda 'data_type' alanı eklenir.
    """
    try:
        from pysvc.unified.client import connect
        from pysvc.errors import (
            UnableToConnectException,
            StorageArrayClientException,
            CommandExecutionError,
        )
    except ImportError:
        print("[HATA] 'pysvc' kütüphanesi yüklü değil. `pip install pysvc` komutuyla yükleyin.", file=sys.stderr)
        return []

    host, user, pwd, port = (
        svc_cfg["host"], svc_cfg["username"], svc_cfg["password"], svc_cfg.get("port", 22)
    )

    try:
        conn = connect(
            address=host,
            username=user,
            password=pwd,
            port=port,
            add_hostkey=True,
            timeout=30,
            cmd_timeout=60,
            flexible=False,
            with_remote_clispec=True,
        )
        # print(f"[SVC] {host} bağlantısı kuruldu.", file=sys.stderr) # NiFi stdout'una karışmaması için stderr'e yönlendirildi
    except (UnableToConnectException, StorageArrayClientException) as exc:
        print(f"[SVC BAĞLANTI HATASI @ {host}] {exc}", file=sys.stderr)
        return []

    endpoints = [
        "lsvdisk", "lsmdiskgrp", "lshost", "lsnodestats", "lsenclosurestats",
        "lssystem", "lsportfc", "lshostvdiskmap", "lsmdisk", "lsoio",
    ]

    all_collected_records = [] # Tüm toplanan kayıtları tutacak liste

    # Dosyaya yazma işlemleri kaldırıldığı için bu satırlara gerek yok
    # out_dir = os.path.join(JSON_BASE_DIR, host)
    # os.makedirs(out_dir, exist_ok=True)

    namespaces = [conn] + [getattr(conn, a) for a in ("cli", "svcinfo") if hasattr(conn, a)]

    for ep in endpoints:
        ns = next((ns for ns in namespaces if hasattr(ns, ep)), None)
        if not ns:
            # print(f"[UYARI] {host}: '{ep}' metodu yok.", file=sys.stderr) # NiFi stdout'una karışmaması için stderr'e yönlendirildi
            continue

        try:
            result = getattr(ns, ep)()
            serializable_result = _make_serializable(result)

            # Eğer sonuç tek bir sözlükse, liste içine al
            if not isinstance(serializable_result, list):
                serializable_result = [serializable_result]
            
            # Her kayda hangi endpoint'ten geldiğini belirten 'data_type' alanı ekle
            for record in serializable_result:
                # Host bilgisini her kayda ekle, böylece veritabanında hangi hosttan geldiği belli olur
                record['host_ip'] = host 
                record['data_type'] = ep
                all_collected_records.append(record)

            # Dosyaya yazma işlemleri kaldırıldığı için bu print satırlarına gerek yok
            # print(f"[{host}] {ep} verisi toplandı.", file=sys.stderr)

        except (CommandExecutionError, Exception) as exc:
            print(f"[HATA] {ep}@{host}: {exc}", file=sys.stderr)

    conn.close()
    return all_collected_records # Toplanan tüm kayıtları döndür

def _make_serializable(obj):
    """Nesneleri JSON serileştirilebilir hale getirir."""
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            import base64
            return f"base64:{base64.b64encode(obj).decode()}"

    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, dict)):
        return [_make_serializable(i) for i in obj]
    for attr in ("raw", "data", "_root", "response", "_items"):
        if hasattr(obj, attr):
            return _make_serializable(getattr(obj, attr))
    return obj

# ---------------------------------------------------------------------------
# 3) IOSTAT DUMP İNDİRME (Bu flowda kullanılmaz, ayrı bir akış gerektirir)
# ---------------------------------------------------------------------------
def fetch_iostat_files(svc_cfg: dict) -> bool:
    """SVC sisteminden I/O stat dump dosyalarını indirir."""
    # Bu fonksiyon bu NiFi akışında kullanılmayacaktır.
    # Ayrı bir NiFi akışı veya Python betiği ile yönetilmelidir.
    print("[UYARI] fetch_iostat_files fonksiyonu bu akışta kullanılmıyor.", file=sys.stderr)
    return False

# ---------------------------------------------------------------------------
# 4) DUMP’LARI ORGANİZE ET + DELTA XML (Bu flowda kullanılmaz, ayrı bir akış gerektirir)
# ---------------------------------------------------------------------------
_pattern_stats = re.compile(r"_stats_([^_]+)_(\d{6})_(\d{6})$")

def organize_and_delta(svc_cfg: dict) -> None:
    """İndirilen dump'ları organize eder ve delta XML'ler üretir."""
    # Bu fonksiyon bu NiFi akışında kullanılmayacaktır.
    # Ayrı bir NiFi akışı veya Python betiği ile yönetilmelidir.
    print("[UYARI] organize_and_delta fonksiyonu bu akışta kullanılmıyor.", file=sys.stderr)
    return

def _find_and_delta(directory: str, typ: str, delta_dir: str) -> None:
    pass # Bu fonksiyon da kullanılmayacak

def _parse_xml(path: str, typ: str):
    pass # Bu fonksiyon da kullanılmayacak

def _is_numeric_field(name: str, typ: str) -> bool:
    pass # Bu fonksiyon da kullanılmayacak

def _compute_deltas(old: Dict, new: Dict) -> Dict:
    pass # Bu fonksiyon da kullanılmayacak

def _write_delta_xml(tree, root, deltas, out_file, typ):
    pass # Bu fonksiyon da kullanılmayacak

def _remove_ns(el):
    pass # Bu fonksiyon da kullanılmayacak

def _delete_processed_files(dir_path: str) -> None:
    pass # Bu fonksiyon da kullanılmayacak

# ---------------------------------------------------------------------------
# 5) ANA AKIŞ
# ---------------------------------------------------------------------------
def main() -> None:
    """Ana program akışını yönetir."""
    args = parse_args()
    systems = load_systems(
        args.config,
        args.hosts,
        args.username,
        args.password,
    )

    all_hosts_data = [] # Tüm hostlardan gelen veriyi toplamak için

    for svc in systems:
        # print(f"\n========== {svc['host']} ==========", file=sys.stderr)
        # print("\n=== AŞAMA 1 : SVC JSON TOPLAMA ===", file=sys.stderr)
        
        host_records = svc_json_dump(svc)
        if not host_records:
            print(f"[{svc['host']}] bağlantı başarısız veya veri toplanamadı.", file=sys.stderr)
            continue
        all_hosts_data.extend(host_records) # Her hosttan gelen veriyi ana listeye ekle

        # IOSTAT DUMP İNDİRME ve DELTA XML ÜRETME aşamaları bu flowda işlenmez.
        # Bu kısımlar için ayrı bir Python betiği veya NiFi akışı oluşturulmalıdır.
        # print(f"\n[{svc['host']}] JSON toplama tamamlandı.", file=sys.stderr)

    # Toplanan tüm verileri tek bir JSON dizisi olarak stdout'a bas
    # Bu, NiFi'deki SplitJson işlemcisi için FlowFile içeriği olacak
    print(json.dumps(all_hosts_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
