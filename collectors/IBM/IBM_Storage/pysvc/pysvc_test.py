#!/usr/bin/env python3
# pysvc_iostats.py
#
# 1) SVC JSON toplama (işlenmiş + _response ham çıktılar)
# 2) En güncel I/O-stat dump’larını indirme
# 3) Dump’ları organize edip delta XML üretme
# 4) YENİ: Delta JSON çıktıları üretme
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
from typing import Dict, List, Tuple, Optional, Union

# ---------------------------------------------------------------------------
# DİZİN SABİTLERİ
# ---------------------------------------------------------------------------
JSON_BASE_DIR       = "./pysvc_unified_outputs"                             # JSON dosyaları
IOSTAT_BASE_DIR     = "/Datalake_Project/IBM/IBM_Storage/pysvc/iostats"     # Ham dump’lar
DELTA_BASE_DIR      = "/Datalake_Project/IBM/IBM_Storage/pysvc/pysvc_unified_outputs" # Δ XML
JSON_DELTA_BASE_DIR = "/Datalake_Project/IBM/IBM_Storage/pysvc/pysvc_unified_outputs_json_deltas" # YENİ: Δ JSON

# ---------------------------------------------------------------------------
# 0) ARGÜMANLAR — -H zorunlu
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="SVC I/O-stat boru hattı (IP listesi zorunludur)")

    p.add_argument(
        "-c", "--config", default="config.json",
        help="Config JSON yolu (vars: config.json)")
    p.add_argument(
        "-H", "--hosts", required=True,
        help="Virgül/boşlukla ayrılmış IP listesi "
             "(örn. 10.3.2.10,10.3.2.11 10.3.2.12)")

    # ----- yeni: kullanıcı adı / parola -----
    p.add_argument("-u", "--username",
                   help="SVC CLI kullanıcı adı (config’i ezer)")
    p.add_argument("-p", "--password",
                   help="SVC CLI parolası (config’i ezer)")
    # ----------------------------------------
    return p.parse_args()

# ---------------------------------------------------------------------------
# 1) CONFIG + ARGÜMANDAN HOST DİZİSİ
# ---------------------------------------------------------------------------
def load_systems(config_path: str,
                 hosts_arg: str,
                 username: Optional[str],
                 password: Optional[str]) -> List[Dict]:
    try:
        # DEĞİŞİKLİK: Doğrudan "IBM-Virtualize" içeriğini alıyoruz
        cli_config = json.load(open(config_path, encoding="utf-8"))["IBM-Virtualize"]
    except (FileNotFoundError, KeyError) as exc:
        print(f"[CONFIG HATASI] {exc}"); sys.exit(1)

    hosts = [h.strip() for h in re.split(r"[,\s]+", hosts_arg) if h.strip()]
    if not hosts:
        print("[ARG] -H/--hosts ile en az bir IP girmelisiniz."); sys.exit(1)

    # common değişkeni artık tam cli_config'i tutacak
    common = cli_config.copy()

    # ----- CLI argümanları config üzerine yazar -----
    if username is not None:
        common["username"] = username
    if password is not None:
        common["password"] = password
    # ------------------------------------------------

    # Her host için ayrı bir sözlük oluştururken,
    # 'host' anahtarını argümandan gelen host ile güncelliyoruz
    # ve diğer ortak ayarları koruyoruz.
    return [{**common, "host": h} for h in hosts]

# ---------------------------------------------------------------------------
# 2) SVC → JSON (+ _response)
# ---------------------------------------------------------------------------
def svc_json_dump(svc_cfg: dict) -> bool:
    from pysvc.unified.client import connect
    from pysvc.errors import (
        UnableToConnectException,
        StorageArrayClientException,
        CommandExecutionError,
    )

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
        print(f"[SVC] {host} bağlantısı kuruldu.")
    except (UnableToConnectException, StorageArrayClientException) as exc:
        print(f"[SVC BAĞLANTI HATASI @ {host}] {exc}")
        return False

    endpoints = [
        "lsvdisk", "lsmdiskgrp", "lshost", "lsnodestats", "lsenclosurestats",
        "lssystem", "lsportfc", "lshostvdiskmap", "lsmdisk", "lsoio",
    ]

    out_dir = os.path.join(JSON_BASE_DIR, host)
    os.makedirs(out_dir, exist_ok=True)

    namespaces = [conn] + [getattr(conn, a) for a in ("cli", "svcinfo") if hasattr(conn, a)]

    for ep in endpoints:
        ns = next((ns for ns in namespaces if hasattr(ns, ep)), None)
        if not ns:
            print(f"[UYARI] {host}: '{ep}' metodu yok."); continue

        try:
            result = getattr(ns, ep)()                          # çıktı objesi
            # --- işlenmiş JSON ---
            main_fp = os.path.join(out_dir, f"{ep}.json")
            with open(main_fp, "w", encoding="utf-8") as f:
                json.dump(_make_serializable(result), f, indent=2, ensure_ascii=False)

            # --- ham/response JSON ---
            resp_obj = None
            for attr in ("response", "raw"):
                if hasattr(result, attr):
                    resp_obj = getattr(result, attr)
                    break
            if resp_obj is not None:
                resp_fp = os.path.join(out_dir, f"{ep}_response.json")
                with open(resp_fp, "w", encoding="utf-8") as f:
                    json.dump(_make_serializable(resp_obj), f,
                              indent=2, ensure_ascii=False)
                extra = " (+_response)"
            else:
                extra = ""

            print(f"[{host}] {ep} → {main_fp}{extra}")

        except (CommandExecutionError, Exception) as exc:
            print(f"[HATA] {ep}@{host}: {exc}")

    conn.close()
    return True

def _make_serializable(obj):
    # --- YENİ: bytes → UTF-8 string ----------------------------------------
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")          # çoğu CLI çıktısı UTF-8
        except UnicodeDecodeError:
            # okunamayan byte dizilerini güvenli bir gösterime çevir
            import base64
            return f"base64:{base64.b64encode(obj).decode()}"
    # -----------------------------------------------------------------------

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
# 3) IOSTAT DUMP İNDİRME
# ---------------------------------------------------------------------------
def fetch_iostat_files(svc_cfg: dict) -> bool:
    host, user, pwd = svc_cfg["host"], svc_cfg["username"], svc_cfg["password"]
    remote_path = svc_cfg.get("remote_path", "/dumps/iostats")
    local_path  = os.path.join(IOSTAT_BASE_DIR, host)
    os.makedirs(local_path, exist_ok=True)

    list_cmd = (
        f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no "
        f"{user}@{host} \"lsdumps -prefix {remote_path}\""
    )
    proc = subprocess.run(list_cmd, shell=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        print(f"[IOSTAT] {host}: {proc.stderr.strip()}"); return False

    files = [ln.split(None, 1)[1].strip()
             for ln in proc.stdout.splitlines() if len(ln.split(None,1)) == 2]
    if not files:
        print(f"[IOSTAT] {host}: dump bulunamadı."); return False

    ts_set = {re.search(r'_(\d{6})$', f).group(1) for f in files if re.search(r'_(\d{6})$', f)}
    top2 = sorted(ts_set, reverse=True)[:2]
    targets = [f for f in files if any(f.endswith(f"_{t}") for t in top2)]

    print(f"[IOSTAT] {host}: {len(targets)} dosya indiriliyor → {local_path}")
    for fname in targets:
        remote_file = os.path.join(remote_path, fname)
        scp_cmd = (
            f"sshpass -p '{pwd}' scp -o StrictHostKeyChecking=no "
            f"{user}@{host}:{remote_file} {local_path}"
        )
        subprocess.run(scp_cmd, shell=True)
    return True

# ---------------------------------------------------------------------------
# 4) DUMP’LARI ORGANİZE ET + DELTA XML/JSON
# ---------------------------------------------------------------------------
_pattern_stats = re.compile(r"_stats_([^_]+)_(\d{6})_(\d{6})$")

def organize_and_delta(svc_cfg: dict) -> None:
    host        = svc_cfg["host"]
    base_dir    = os.path.join(IOSTAT_BASE_DIR, host)
    delta_dir   = os.path.join(DELTA_BASE_DIR,  host)
    json_delta_dir = os.path.join(JSON_DELTA_BASE_DIR, host) # YENİ: JSON delta dizini
    os.makedirs(delta_dir, exist_ok=True)
    os.makedirs(json_delta_dir, exist_ok=True) # YENİ: JSON delta dizini oluştur

    if not os.path.isdir(base_dir):
        print(f"[ORGA] {base_dir} bulunamadı, atlandı."); return

    file_map: Dict[str, List[Tuple[str, str]]] = {}
    ts_set = set()

    for fn in os.listdir(base_dir):
        m = _pattern_stats.search(fn)
        if m:
            uniq, date, time = m.groups()
            ts = f"{date}{time}"
            ts_set.add(ts)
            file_map.setdefault(uniq, []).append((fn, ts))

    if len(ts_set) < 2:
        print(f"[ORGA] {host}: karşılaştıracak ≥2 zaman damgası yok."); return

    top2 = sorted(ts_set, reverse=True)[:2]
    print(f"[ORGA] {host}: seçilen zaman damgaları → {top2}")

    created_dirs = []
    for uniq, items in file_map.items():
        folder = os.path.join(base_dir, uniq)
        os.makedirs(folder, exist_ok=True)
        for fn, ts in items:
            if ts in top2:
                shutil.move(os.path.join(base_dir, fn), os.path.join(folder, fn))
        created_dirs.append(folder)

    for folder in created_dirs:
        for prefix in ("Nv", "Nm", "Nn", "Nd"):
            _find_and_delta(folder, prefix, delta_dir, json_delta_dir) # DEĞİŞİKLİK: json_delta_dir eklendi
        # _delete_processed_files(folder) # Bu satır önceki istek üzerine kapatıldı.

    print(f"[DELTA] {host}: tamam.")

# DEĞİŞİKLİK: _find_and_delta fonksiyonuna json_delta_dir eklendi
def _find_and_delta(directory: str, typ: str, delta_dir: str, json_delta_dir: str) -> None:
    patt = re.compile(rf"^({typ})_stats_([^_]+)_(\d{{6}})_(\d{{6}})$")
    groups: Dict[str, List[Tuple[str, str, str]]] = {}

    for fn in os.listdir(directory):
        m = patt.match(fn)
        if m:
            pre, node, dt, tm = m.groups()
            groups.setdefault(f"{pre}_stats_{node}", []).append((fn, dt, tm))

    for key, lst in groups.items():
        if len(lst) < 2:
            continue
        lst.sort(key=lambda x: (x[1], x[2]))
        old_fn, new_fn = lst[-2][0], lst[-1][0]

        old_tree, _, old_data = _parse_xml(os.path.join(directory, old_fn), typ)
        new_tree, root, new_data = _parse_xml(os.path.join(directory, new_fn), typ)
        # DEĞİŞİKLİK: _compute_deltas çağrısına 'typ' parametresi eklendi
        deltas = _compute_deltas(old_data, new_data, typ)

        # XML çıktısı
        out_file_xml = os.path.join(delta_dir, f"{key}_delta.xml")
        _write_delta_xml(new_tree, root, deltas, out_file_xml, typ)
        print(f"[ΔXML] {out_file_xml} yazıldı.")

        # YENİ: JSON çıktısı
        out_file_json = os.path.join(json_delta_dir, f"{key}_delta.json")
        _write_delta_json(deltas, out_file_json, typ) # YENİ: JSON yazdırma fonksiyonu
        print(f"[ΔJSON] {out_file_json} yazıldı.")

# DEĞİŞİKLİK: _parse_xml fonksiyonu tüm öznitelikleri yakalayacak şekilde güncellendi
def _parse_xml(path: str, typ: str):
    tree = ET.parse(path)
    root = tree.getroot()
    _remove_ns(root)

    selector = {"Nd": ".//mdsk", "Nm": ".//mdsk",
                "Nv": ".//vdsk", "Nn": ".//node"}[typ]
    id_attr  = {"Nd": "idx",   "Nm": "id",
                "Nv": "id",    "Nn": "id"}[typ]

    data: Dict[str, Dict[str, Union[int, str]]] = {} # int veya str içerebilir
    for el in root.findall(selector):
        idx = el.get(id_attr)
        data.setdefault(idx, {})
        for k, v in el.attrib.items():
            if _is_numeric_field(k, typ):
                try:
                    data[idx][k] = int(v)
                except ValueError:
                    data[idx][k] = v # Sayısal değilse string olarak sakla
            else:
                data[idx][k] = v # Sayısal olmayanları da string olarak sakla
    return tree, root, data

def _is_numeric_field(name: str, typ: str) -> bool:
    base = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq",
            "ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo",
            "rxl", "wxl"]
    extra_nv = ["rl", "wl", "rlw", "wlw"]
    return name in base + (extra_nv if typ == "Nv" else [])

# DEĞİŞİKLİK: _compute_deltas fonksiyonu tüm öznitelikleri koruyacak şekilde güncellendi
def _compute_deltas(old: Dict, new: Dict, typ: str) -> Dict: # 'typ' parametresi eklendi
    result = {}
    for idx in new:
        result.setdefault(idx, {})
        for k, new_val in new[idx].items():
            if _is_numeric_field(k, typ): # 'typ' parametresi kullanıldı
                old_val = old.get(idx, {}).get(k, 0)
                if isinstance(new_val, int) and isinstance(old_val, int):
                    result[idx][k] = new_val - old_val
                else:
                    # Sayısal olmayan veya tür uyuşmazlığı durumunda yeni değeri kopyala
                    result[idx][k] = new_val
            else: # Sayısal olmayan alan, yeni veriden doğrudan kopyala
                result[idx][k] = new_val
    return result

def _write_delta_xml(tree, root, deltas, out_file, typ):
    selector = {"Nd": ".//mdsk", "Nm": ".//mdsk",
                "Nv": ".//vdsk", "Nn": ".//node"}[typ]
    id_attr  = {"Nd": "idx",   "Nm": "id",
                "Nv": "id",    "Nn": "id"}[typ]

    for el in root.findall(selector):
        idx = el.get(id_attr)
        for k, v in deltas.get(idx, {}).items():
            el.set(k, str(v))
    tree.write(out_file, encoding="utf-8", xml_declaration=True)

# YENİ: _write_delta_json fonksiyonu
def _write_delta_json(deltas: Dict, out_file: str, typ: str) -> None:
    # İhtiyaç duyarsanız, JSON çıktısının yapısını burada ayarlayabilirsiniz.
    # Örneğin, "type" bilgisini de ekleyebiliriz.
    json_output = {
        "type": typ,
        "deltas": deltas
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    # print(f"[JSON DELTA] {out_file} yazıldı.") # Bu satırın çıktısı _find_and_delta içinde yönetiliyor

def _remove_ns(el):
    if el.tag.startswith("{"):
        el.tag = el.tag.split("}", 1)[1]
    for ch in el:
        _remove_ns(ch)

def _delete_processed_files(dir_path: str) -> None:
    for fn in os.listdir(dir_path):
        fp = os.path.join(dir_path, fn)
        if os.path.isfile(fp):
            os.remove(fp)

# ---------------------------------------------------------------------------
# 5) ANA AKIŞ
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()
    systems = load_systems(
        args.config,
        args.hosts,
        args.username,
        args.password,
    )

    for svc in systems:
        host = svc["host"]
        print(f"\n========== {host} ==========")

        print("\n=== AŞAMA 1 : SVC JSON TOPLAMA ===")
        if not svc_json_dump(svc):
            print(f"[{host}] bağlantı başarısız; diğer aşamalar atlandı.")
            continue

        print("\n=== AŞAMA 2 : IOSTAT DUMP İNDİRME ===")
        if not fetch_iostat_files(svc):
            print(f"[{host}] dump indirilemedi; delta aşaması atlandı.")
            continue

        print("\n=== AŞAMA 3 : DELTA XML/JSON ÜRETME ===") # YENİ: Başlık güncellendi
        organize_and_delta(svc)

        print(f"\n[{host}] Tüm aşamalar başarıyla tamamlandı.")

if __name__ == "__main__":
    main()
