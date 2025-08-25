#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nutanix snapshot & schedule bilgilerini çekip
public.nutanix_snapshot_schedule_metrics tablosu için INSERT komutları üretir.
STDOUT ⇒ Yalnızca INSERT cümleleri  (NiFi FlowFile içeriği)
STDERR ⇒ Bilgi / log satırları          (NiFi processor log’unda görünür)

27 Mayıs 2025 güncellemesi
---------------------------------
* **dr_snapshots** endpoint’inden eklenen alanlar
  - snapshot_create_time_usecs
  - snapshot_expiry_time_usecs
  - snapshot_id
  - exclusive_usage_in_bytes

* **schedules** endpoint’inden eklenen alanlar
  - user_start_time_in_usecs
  - remote_max_snapshots (dict)
  - id
  - local_retention_period
  - remote_retention_period (dict)
  - local_retention_type
  - remote_retention_type
  - suspended

INSERT cümleleri bu alanları da kapsar.
DUPLİKASYON ÖNLEME: Bu versiyon, PostgreSQL'in ON CONFLICT DO NOTHING özelliğini kullanarak
veri duplikasyonunu engeller; mevcut kayıtları güncellemez, sadece yeni kayıtları ekler.
"""

import base64
import json
import sys
from pathlib import Path
from urllib.parse import quote
import requests # datetime modülüne bu senaryoda gerek yok, o yüzden kaldırdım

# --------------------------------------------------------------------------- #
# 0) Yardımcı: log()  (sadece STDERR)
# --------------------------------------------------------------------------- #
def log(msg: str):
    """Bilgi satırlarını STDERR'a yazar; NiFi FlowFile'ına girmez."""
    print(msg, file=sys.stderr, flush=True)

# --------------------------------------------------------------------------- #
# 1) Konfigürasyon
# --------------------------------------------------------------------------- #
CONFIG_PATH = "/Datalake_Project/configuration_file.json"

try:
    cfg = json.loads(Path(CONFIG_PATH).read_text())
    nutanix = cfg["Nutanix"]

    PRISM_IPS = [ip.strip() for ip in nutanix["PRISM_IP"].split(",") if ip.strip()]
    USERNAME  = nutanix["USERNAME"]
    PASSWORD  = nutanix["PASSWORD"]
except FileNotFoundError:
    log(f"[ERROR] Konfigürasyon dosyası bulunamadı: {CONFIG_PATH}")
    sys.exit(1)
except json.JSONDecodeError:
    log(f"[ERROR] Konfigürasyon dosyası JSON formatında değil: {CONFIG_PATH}")
    sys.exit(1)
except KeyError as e:
    log(f"[ERROR] Konfigürasyon dosyasında eksik anahtar: {e}. Lütfen PRISM_IP, USERNAME, PASSWORD alanlarını kontrol edin.")
    sys.exit(1)


# TLS uyarılarını kapat
requests.packages.urllib3.disable_warnings()
REQ_TIMEOUT = 10  # saniye

def get_auth_headers(user, pwd):
    # base64.b64enocode düzeltildi -> base64.b64encode
    token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

def safe(val):
    """None / 'None' / 'null'  →  None,  geri kalanı olduğu gibi"""
    if val is None:
        return None
    if isinstance(val, str) and val.strip().lower() in ("none", "null"):
        return None
    return val

# --------------------------------------------------------------------------- #
# 2) Nutanix API çağrıları
# --------------------------------------------------------------------------- #
def fetch_snapshot_info(ip):
    """dr_snapshots endpoint’inden gerekli verileri çeker."""
    url = f"https://{ip}:9440/PrismGateway/services/rest/v2.0/protection_domains/dr_snapshots"
    try:
        r = requests.get(url, headers=get_auth_headers(USERNAME, PASSWORD),
                         verify=False, timeout=REQ_TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        log(f"[ERROR] Nutanix API çağrısı sırasında hata ({ip}): {e}")
        return []

    snapshots = []
    for e in r.json().get("entities", []):
        snapshots.append({
            "protection_domain_name":        safe(e.get("protection_domain_name")),
            "state":                         safe(e.get("state")),
            "size_in_bytes":                 e.get("size_in_bytes"),
            "exclusive_usage_in_bytes":      e.get("exclusive_usage_in_bytes"),
            "snapshot_id":                   safe(e.get("snapshot_id")),
            "snapshot_create_time_usecs":    e.get("snapshot_create_time_usecs"),
            "snapshot_expiry_time_usecs":    e.get("snapshot_expiry_time_usecs"),
            "missing_entities":              e.get("missing_entities") or [],
            "vm_names": [safe(v.get("vm_name")) for v in (e.get("vms") or [])
                         if isinstance(v, dict) and safe(v.get("vm_name"))]
        })
    return snapshots


def fetch_pd_schedules(ip, pd_name):
    """Belirli bir Protection Domain’in schedule bilgisini çeker."""
    url = (f"https://{ip}:9440/PrismGateway/services/rest/v2.0/"
           f"protection_domains/{quote(pd_name)}/schedules")
    try:
        r = requests.get(url, headers=get_auth_headers(USERNAME, PASSWORD),
                         verify=False, timeout=REQ_TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        log(f"[WARN] Schedule alınamadı ({pd_name}@{ip}): {exc}")
        return []

    items = r.json() if isinstance(r.json(), list) else r.json().get("entities", [])
    out = []
    for s in items:
        rp = s.get("retention_policy") or {}
        out.append({
            "type":                      safe(s.get("type")),
            "every_nth":                 s.get("every_nth"),
            "user_start_time_in_usecs":  s.get("user_start_time_in_usecs"),
            "start_times_in_usecs":      s.get("start_times_in_usecs"),
            "end_time_in_usecs":         s.get("end_time_in_usecs"),
            "id":                        safe(s.get("id")), # Schedule ID'si
            "suspended":                 s.get("suspended"),
            "local_max_snapshots":       rp.get("local_max_snapshots"),
            "remote_max_snapshots":      rp.get("remote_max_snapshots"),
            "local_retention_period":    rp.get("local_retention_period"),
            "remote_retention_period":   rp.get("remote_retention_period"),
            "local_retention_type":      rp.get("local_retention_type"),
            "remote_retention_type":     rp.get("remote_retention_type")
        })
    return out

# --------------------------------------------------------------------------- #
# 3) INSERT cümlesi üreten fonksiyon (ON CONFLICT DO NOTHING ile)
# --------------------------------------------------------------------------- #
def generate_insert_statements(records,
                               table_name="public.nutanix_snapshot_schedule_metrics"):
    """Her snapshot/schedule kaydı için TEK satır INSERT ... ON CONFLICT DO NOTHING döner.

    - vm_names                → virgülle birleştirilmiş metin
    - missing_entities_* → virgülle birleştirilmiş metinler
    - *remote_* alanları      → JSON stringify edilmiş metin
    """
    def q(v):
        if v is None:
            return "NULL"
        # Escape single quotes by doubling them
        return "'" + str(v).replace("'", "''") + "'"

    ins = []
    for rec in records:
        # VM adlarını birleştir
        vm_join = ", ".join(rec.get("vm_names", []))

        # Eksik varlık listelerini ayıkla
        miss_list = rec.get("missing_entities") or []
        ent_names = ", ".join(
            [m.get("entity_name") for m in miss_list if safe(m.get("entity_name"))]
        ) or None
        ent_types = ", ".join(
            [m.get("entity_type") for m in miss_list if safe(m.get("entity_type"))]
        ) or None
        cg_names = ", ".join(
            [m.get("cg_name") for m in miss_list if safe(m.get("cg_name"))]
        ) or None

        values_str = (
            f"{q(rec['prism_ip'])}, "
            f"{q(rec['protection_domain_name'])}, "
            f"{q(rec['state'])}, "
            f"{q(ent_names)}, "
            f"{q(ent_types)}, "
            f"{q(cg_names)}, "
            f"{rec.get('size_in_bytes') or 0}, "
            f"{rec.get('exclusive_usage_in_bytes') or 0}, "
            f"{q(rec.get('snapshot_id'))}, "
            f"{rec.get('snapshot_create_time_usecs') or 'NULL'}, "
            f"{rec.get('snapshot_expiry_time_usecs') or 'NULL'}, "
            f"{q(vm_join)}, "
            f"{q(rec.get('type'))}, " # schedule_type
            f"{rec.get('every_nth') or 'NULL'}, " # schedule_every_nth
            f"{rec.get('user_start_time_in_usecs') or 'NULL'}, " # schedule_user_start_time_in_usecs
            f"{(rec.get('start_times_in_usecs') or [None])[0] or 'NULL'}, " # schedule_start_times_in_usecs
            f"{rec.get('end_time_in_usecs') or 'NULL'}, " # schedule_end_time_in_usecs
            f"{q(rec.get('id'))}, " # schedule_id
            f"{'TRUE' if rec.get('suspended') else ('FALSE' if rec.get('suspended') is False else 'NULL')}, " # schedule_suspended (BOOLEAN)
            f"{rec.get('local_max_snapshots') or 'NULL'}, " # schedule_local_max_snapshots
            f"{q(json.dumps(rec.get('remote_max_snapshots') or {}))}, " # schedule_remote_max_snapshots (JSON)
            f"{rec.get('local_retention_period') or 'NULL'}, " # schedule_local_retention_period
            f"{q(json.dumps(rec.get('remote_retention_period') or {}))}, " # schedule_remote_retention_period (JSON)
            f"{q(rec.get('local_retention_type'))}, " # schedule_local_retention_type
            f"{q(rec.get('remote_retention_type'))}" # schedule_remote_retention_type
        )

        stmt = (
            f"INSERT INTO {table_name} ("
            # --------------- kolon listesi ---------------
            "nutanix_ip, protection_domain_name, state, "
            "missing_entities_entity_name, missing_entities_entity_type, missing_entities_cg_name, "
            "size_in_bytes, exclusive_usage_in_bytes, "
            "snapshot_id, snapshot_create_time_usecs, snapshot_expiry_time_usecs, "
            "vm_names, "
            "schedule_type, schedule_every_nth, "
            "schedule_user_start_time_in_usecs, "
            "schedule_start_times_in_usecs, schedule_end_time_in_usecs, "
            "schedule_id, schedule_suspended, "
            "schedule_local_max_snapshots, schedule_remote_max_snapshots, "
            "schedule_local_retention_period, schedule_remote_retention_period, "
            "schedule_local_retention_type, schedule_remote_retention_type"
            ") VALUES ("
            f"{values_str}"
            f") ON CONFLICT (nutanix_ip, protection_domain_name, snapshot_id, snapshot_create_time_usecs) DO NOTHING;"
        )
        ins.append(stmt)

    return ins

# --------------------------------------------------------------------------- #
# 4) main()
# --------------------------------------------------------------------------- #
def main():
    all_records = []

    for ip in PRISM_IPS:
        log(f"→ {ip} adresi işleniyor…")
        try:
            for snap in fetch_snapshot_info(ip):
                pd = snap["protection_domain_name"]
                schedules = fetch_pd_schedules(ip, pd) if pd else []
                # Schedule yoksa snapshot tek başına girsin
                # Bu durumda schedule ile ilgili tüm alanları NULL olarak işaretliyoruz
                if not schedules:
                    all_records.append({
                        **snap,
                        "prism_ip": ip,
                        "id": None, # schedule_id
                        "type": None, # schedule_type
                        "every_nth": None,
                        "user_start_time_in_usecs": None,
                        "start_times_in_usecs": None,
                        "end_time_in_usecs": None,
                        "suspended": None,
                        "local_max_snapshots": None,
                        "remote_max_snapshots": None,
                        "local_retention_period": None,
                        "remote_retention_period": None,
                        "local_retention_type": None,
                        "remote_retention_type": None
                    })
                else:
                    for sch in schedules:
                        all_records.append({**snap, "prism_ip": ip, **sch})
        except Exception as exc:
            log(f"[ERROR] {ip} işlenirken hata: {exc}")

    log(f"Toplam {len(all_records)} snapshot/schedule kaydı işlendi.")

    # INSERT'leri STDOUT'a bas
    for stmt in generate_insert_statements(all_records): # Fonksiyon adı generate_insert_statements olarak değiştirildi
        print(stmt)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
