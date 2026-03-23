import requests
import json
import argparse
import sys
import urllib3
import logging
import re
from datetime import datetime, timezone

# Loglama ayarları (Loglar ekranda kalır, veri dosyaya veya stdout'a gider)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s', stream=sys.stderr)

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Datalake için Standart İsimlendirme Sözlüğü (Mapping)
# Zabbix'ten gelen item ismini (küçük harfe çevrilmiş haliyle) arar ve Datalake sütun ismine eşler.
GENERIC_METRIC_MAP = {
    "icmp ping": "icmp_status",
    "ping status": "icmp_status",
    "icmp loss": "icmp_loss_pct",
    "icmp response time": "icmp_response_time_ms",
    "cpu utilization": "cpu_utilization_pct",
    "memory utilization": "memory_utilization_pct",
    "swap utilization": "memory_swap_utilization_pct",
    "uptime": "uptime_seconds",
    "system name": "system_name",
    "system description": "system_description"
}

# Interface regex: Örn: "Interface GigabitEthernet1/0/1(ARI_LEASING_BACKUP_PORT): Duplex status"
# Grup 1: Port Adı, Grup 2: Alias (Opsiyonel), Grup 3: Metrik Adı
IFACE_PATTERN = re.compile(r"Interface\s+([^\(]+)(?:\(([^)]+)\))?:\s+(.*)")

def zabbix_request(url, method, params, auth_token=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    if auth_token:
        payload["auth"] = auth_token
        
    logging.debug(f"İstek atılıyor: {method}")
    try:
        response = requests.post(url, json=payload, timeout=120, verify=False)
        res_json = response.json()
        
        if 'error' in res_json:
            logging.error(f"Zabbix API Hatası ({method}): {json.dumps(res_json['error'])}")
            
        return res_json
    except requests.exceptions.Timeout:
        logging.error("ZABBIX ZAMAN AŞIMI: İstek 120 saniyede tamamlanamadı.")
        return {"error": {"message": "Timeout"}}
    except Exception as e:
        logging.error(f"Bağlantı Hatası: {str(e)}")
        return {"error": {"message": str(e)}}

def parse_numeric(val, unit, metric_name):
    """Zabbix raw değerlerini Datalake için uygun formata (Float/Int) çevirir"""
    if val is None or val == "":
        return None
        
    try:
        f_val = float(val)
        # Saniye cinsinden gelen ping süresini milisaniyeye (ms) çevir
        if unit == 's' and "response time" in metric_name.lower():
            f_val = f_val * 1000
        
        # Eğer sayı tam sayı ise int yap, değilse float bırak
        return int(f_val) if f_val.is_integer() else round(f_val, 4)
    except ValueError:
        return val # Dönüşemiyorsa string olarak bırak (Örn: System name)

def main():
    parser = argparse.ArgumentParser(description="Zabbix Data Exporter for NiFi (Flat JSON)")
    parser.add_argument("--ip", required=True, help="Zabbix sunucu IP adresi")
    parser.add_argument("--user", required=True, help="Zabbix kullanıcı adı")
    parser.add_argument("--password", required=True, help="Zabbix şifresi")
    parser.add_argument("--group", required=True, help="Çekilecek host grubu")
    parser.add_argument("--template", required=False, help="Sadece belirli bir template'e ait verileri çek")
    parser.add_argument("--output", required=False, help="Verilerin kaydedileceği dosya adı (Opsiyonel)")
    
    args = parser.parse_args()
    api_url = f"http://{args.ip}/api_jsonrpc.php"

    logging.info("Adım 1: Zabbix API'ye giriş yapılıyor...")
    login_res = zabbix_request(api_url, "user.login", {"username": args.user, "password": args.password})
    if "error" in login_res:
        login_res = zabbix_request(api_url, "user.login", {"user": args.user, "password": args.password})
    
    auth_token = login_res.get('result')
    if not auth_token:
        logging.critical("Giriş BAŞARISIZ!")
        sys.exit(1)
    logging.info("Giriş BAŞARILI. Auth Token alındı.")

    logging.info(f"Adım 2: '{args.group}' ID'si aranıyor...")
    group_res = zabbix_request(api_url, "hostgroup.get", {
        "filter": {"name": [args.group]},
        "output": ["groupid"]
    }, auth_token)

    if not group_res.get('result'):
        logging.critical(f"'{args.group}' isminde grup BULUNAMADI.")
        sys.exit(1)
    
    group_id = group_res['result'][0]['groupid']
    logging.info(f"Grup BULUNDU (ID: {group_id})")

    # Template ID'sini al (Eğer argüman verildiyse)
    template_id = None
    if args.template:
        tmpl_res = zabbix_request(api_url, "template.get", {
            "filter": {"host": [args.template]}, 
            "output": ["templateid"]
        }, auth_token)
        
        if tmpl_res.get('result'):
            template_id = tmpl_res['result'][0]['templateid']
            logging.info(f"Template '{args.template}' filtreleniyor (ID: {template_id})")
        else:
            logging.warning(f"Template '{args.template}' bulunamadı. Filtreleme yapılmayacak.")

    logging.info("Adım 3: Hostlar ve metrikler çekiliyor (Lütfen bekleyin)...")
    params = {
        "groupids": group_id,
        "output": ["hostid", "name"],
        "selectItems": ["name", "lastvalue", "units"],
        "selectTags": "extend",
        "selectParentTemplates": ["templateid", "name"]
    }
    
    if template_id:
        params["templateids"] = template_id

    hosts_res = zabbix_request(api_url, "host.get", params, auth_token)
    raw_hosts = hosts_res.get('result', [])
    logging.info(f"Sorgu tamamlandı. Dönen host sayısı: {len(raw_hosts)}")

    results = []
    # Tüm kayıtlar için ortak snapshot zamanı
    collection_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for host in raw_hosts:
        # 1. Metadata Hazırlığı
        location = "N/A"
        loki_id = "N/A"
        for t in host.get('tags', []):
            tag_name = t['tag'].lower()
            if tag_name in ['location', 'city']:
                location = t['value']
            elif tag_name == 'loki_id':
                loki_id = t['value']
        
        # Template listesini JSON string olarak sakla
        templates = [t['name'] for t in host.get('parentTemplates', [])]
        templates_str = json.dumps(templates) if templates else None

        # Geçici ayrıştırma sözlükleri
        temp_device_metrics = {}
        temp_interfaces = {}

        # 2. İtem'ları Ayrıştırma
        for i in host.get('items', []):
            item_name = i['name']
            raw_val = i.get('lastvalue', '')
            unit = i.get('units', '')
            
            parsed_val = parse_numeric(raw_val, unit, item_name)
            if parsed_val is None:
                continue

            # Arayüz (Interface) verisi mi?
            iface_match = IFACE_PATTERN.match(item_name)
            if iface_match:
                if_name, if_alias, if_metric = iface_match.groups()
                if_name = if_name.strip()
                
                if if_name not in temp_interfaces:
                    temp_interfaces[if_name] = {
                        "interface_name": if_name,
                        "interface_alias": if_alias.strip() if if_alias else "N/A"
                    }
                
                # Metrik ismini standartlaştır (boşlukları _ yap)
                std_metric_name = if_metric.lower().replace(" ", "_").replace("-", "_")
                temp_interfaces[if_name][std_metric_name] = parsed_val
            
            # Değilse Genel Cihaz Metriği mi?
            else:
                lower_name = item_name.lower()
                for key_match, std_name in GENERIC_METRIC_MAP.items():
                    if key_match in lower_name:
                        temp_device_metrics[std_name] = parsed_val
                        break

        # 3. Ağ Toplamlarını Hesaplama
        total_ports = len(temp_interfaces)
        active_ports = 0
        for iface in temp_interfaces.values():
            status = iface.get('duplex_status', iface.get('operational_status', 0))
            if status in [1, 3]: 
                active_ports += 1

        # 4. NiFi İçin Düz (Flat) Kayıtları Oluşturma
        
        # --- A. CİHAZ KAYDI (Device Record) ---
        device_record = {
            "data_type": "network_device",
            "collection_timestamp": collection_time,
            "host": host['name'],
            "location": location,
            "loki_id": loki_id,
            "applied_templates": templates_str,
            "total_ports_count": total_ports,
            "active_ports_count": active_ports
        }
        device_record.update(temp_device_metrics)
        results.append(device_record)

        # --- B. ARAYÜZ KAYITLARI (Interface Records) ---
        for iface in temp_interfaces.values():
            iface_record = {
                "data_type": "network_interface",
                "collection_timestamp": collection_time,
                "host": host['name']
            }
            iface_record.update(iface)
            results.append(iface_record)

    logging.info("Adım 4: İşlem tamamlanıyor, JSON oluşturuluyor...")
    
    # ensure_ascii=False ile Türkçe vb. karakter bozulmalarını önlüyoruz
    json_data = json.dumps(results, indent=2, ensure_ascii=False)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_data)
            logging.info(f"BAŞARILI: Tüm veriler '{args.output}' dosyasına kaydedildi!")
        except IOError as e:
            logging.error(f"Dosyaya yazma hatası: {e}")
    else:
        # NiFi ExecuteStreamCommand direkt olarak stdout'u okur.
        print(json_data)

if __name__ == "__main__":
    main()
