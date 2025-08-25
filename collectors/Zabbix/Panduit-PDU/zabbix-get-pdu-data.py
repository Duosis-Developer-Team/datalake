# -*- coding: utf-8 -*-
import requests
import json
import argparse
import sys
import re
import time
from getpass import getpass
from collections import defaultdict
from datetime import datetime, timezone

# SSL sertifika doğrulama hatalarını bastırmak için
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class ZabbixAPIClient:
    """
    Zabbix API ile etkileşim kurmak için bir istemci sınıfı.
    """
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json-rpc'})
        self.auth_token = None
        self.request_id = 1
        self.server_url = None

    def _send_request(self, method, params):
        """Zabbix API'ye JSON-RPC isteği gönderir."""
        payload = {
            "jsonrpc": "2.0", "method": method, "params": params,
            "id": self.request_id
        }
        if self.auth_token:
            payload['auth'] = self.auth_token
        try:
            response = self.session.post(self.server_url, data=json.dumps(payload), timeout=60, verify=False)
            response.raise_for_status()
            result = response.json()
            if 'error' in result:
                sys.exit(f"Zabbix API Hatası: {result['error']['data']}")
            self.request_id += 1
            return result.get('result')
        except json.JSONDecodeError:
            sys.exit("Hata: Sunucudan gelen yanıt JSON formatında değil.")
        except requests.exceptions.RequestException as e:
            raise e

    def login(self):
        """API'ye önce HTTPS, sonra HTTP üzerinden bağlanmayı dener."""
        params = {"username": self.username, "password": self.password}
        urls_to_try = [f"https://{self.hostname}/zabbix/api_jsonrpc.php", f"http://{self.hostname}/zabbix/api_jsonrpc.php"]
        for url in urls_to_try:
            self.server_url = url
            print(f"Bağlantı deneniyor: {self.server_url}", file=sys.stderr)
            try:
                self.auth_token = self._send_request("user.login", params)
                if self.auth_token:
                    print("Giriş başarılı.", file=sys.stderr)
                    return
            except requests.exceptions.RequestException:
                print(f"Bağlantı başarısız.", file=sys.stderr)
        sys.exit("Bağlantı Hatası: Sunucuya ulaşılamadı. Hostname'i ve ağ ayarlarını kontrol edin.")

    def get_data_for_group(self, group_id):
        """Belirtilen gruptaki tüm hostları ve bu hostlara ait item'ları alır."""
        print(f"'{group_id}' ID'li gruptaki hostlar alınıyor...", file=sys.stderr)
        hosts = self._send_request("host.get", {"output": ["hostid", "host", "name", "status"], "groupids": group_id})
        print(f"Toplam {len(hosts)} adet host bulundu.", file=sys.stderr)
        if not hosts: return []
        
        host_ids = [host['hostid'] for host in hosts]
        print(f"{len(host_ids)} adet host için item'lar alınıyor...", file=sys.stderr)
        items = self._send_request("item.get", {"output": "extend", "hostids": host_ids, "sortfield": "name"})
        print(f"Toplam {len(items)} adet item bulundu.", file=sys.stderr)

        raw_data = []
        for host in hosts:
            host_items = [item for item in items if item['hostid'] == host['hostid']]
            raw_data.append({"host_info": host, "items": host_items})
        return raw_data

    def logout(self):
        """API oturumunu sonlandırır."""
        if self.auth_token:
            print("Oturum sonlandırılıyor...", file=sys.stderr)
            try: self._send_request("user.logout", [])
            except requests.exceptions.RequestException: pass
            print("Oturum başarıyla kapatıldı.", file=sys.stderr)

def clean_metric_name(s):
    """Metrik isimlerini temizler ve standart bir formata getirir."""
    s = s.strip().replace(" ", "_").lower()
    s = re.sub(r'[^a-z0-9_]', '', s)
    s = re.sub(r'_{2,}', '_', s)
    return s

def parse_pdu_name(pdu_name):
    """'FR2-524-PDU-B' formatındaki PDU ismini ayrıştırır."""
    if not pdu_name:
        return {"location": None, "rack_id": None, "pdu_index": None}
    parts = pdu_name.split('-')
    if len(parts) >= 3:
        return {
            "location": parts[0],
            "rack_id": parts[1],
            "pdu_index": '-'.join(parts[2:])
        }
    return {"location": None, "rack_id": None, "pdu_index": pdu_name}

def transform_data(raw_data):
    """Ham Zabbix verisini hedeflenen, temiz ve dikey formata dönüştürür."""
    print("Veri yapılandırılıyor...", file=sys.stderr)
    final_output_list = []
    collection_timestamp = datetime.now(timezone.utc).isoformat()

    INVENTORY_KEYS = ["device_model", "firmware_version", "hardware_version", "system_name", "breaker_count", "outlet_count", "door_count", "dry_count", "hid_count", "humidity_count", "input_phase_count", "rope_count", "spot_count", "temperature_count"]

    for host_data in raw_data:
        host_info, items = host_data.get("host_info", {}), host_data.get("items", [])
        host_id, zabbix_host_name = host_info.get("hostid"), host_info.get("name")
        if not host_id: continue

        # HATA DÜZELTMESİ: Her bir veri tipi için ayrı ve doğru şekilde defaultdict tanımlandı.
        temp_data = {
            "inventory": {}, "input_metrics": {}, "global_metrics": {}, "powershare": {},
            "breakers": defaultdict(dict),
            "outlets": defaultdict(dict),
            "sensors": defaultdict(lambda: defaultdict(dict)), # 3 seviyeli sensör verisi için
            "phases": defaultdict(dict),
            "hids": defaultdict(dict)
        }

        system_name_from_device = None
        
        for item in items:
            item_name, item_value = item.get("name", ""), item.get("lastvalue")
            if "system name" in item_name.lower() and item_value:
                system_name_from_device = item_value

            m_breaker = re.match(r"Group \(Breaker\)\s+([\d\.]+)\s+(.*)", item_name)
            m_phase = re.match(r"Input Phase\s+([\d\.]+)\s+(.*)", item_name)
            m_outlet = re.match(r"Outlet:?\s*(?:OUTLET)?\s*(\d+)\s*(.*)", item_name)
            m_sensor = re.match(r"(Temperature|Humidity|Door|Dry|Rope|Spot)\s*(?:Probe)?\s*([\d\.]+)\s+(.*)", item_name)
            m_hid = re.match(r"HID\s+([\d\.]+)\s+(.*)", item_name)

            if m_breaker: temp_data["breakers"][m_breaker.group(1)][clean_metric_name(m_breaker.group(2))] = item_value
            elif m_phase: temp_data["phases"][m_phase.group(1)][clean_metric_name(m_phase.group(2))] = item_value
            elif m_outlet: temp_data["outlets"][f"OUTLET{m_outlet.group(1)}"][clean_metric_name(re.sub(r'\s{2,}', ' ', m_outlet.group(2)).strip())] = item_value
            elif m_sensor: temp_data["sensors"][m_sensor.group(1)][m_sensor.group(2)][clean_metric_name(m_sensor.group(3))] = item_value
            elif m_hid: temp_data["hids"][m_hid.group(1)][clean_metric_name(m_hid.group(2))] = item_value
            elif clean_metric_name(item_name) in INVENTORY_KEYS: temp_data["inventory"][clean_metric_name(item_name)] = item_value
            elif item_name.lower().startswith("input"): temp_data["input_metrics"][clean_metric_name(item_name.replace("Input ", ""))] = item_value
            elif "powershare" in item_name.lower(): temp_data["powershare"][clean_metric_name(item_name.replace("Powershare ", ""))] = item_value
            else: temp_data["global_metrics"][clean_metric_name(item_name)] = item_value
        
        pdu_name = system_name_from_device or zabbix_host_name
        base_info = {"collection_timestamp": collection_timestamp, "pdu_id": host_id, "pdu_name": pdu_name, "zabbix_host_name": zabbix_host_name}
        
        if temp_data["inventory"]:
            parsed_name_info = parse_pdu_name(pdu_name)
            temp_data["inventory"].update(parsed_name_info)
            final_output_list.append({**base_info, "data_type": "pdu_inventory", **temp_data["inventory"]})

        if temp_data["input_metrics"]: final_output_list.append({**base_info, "data_type": "pdu_input_metrics", **temp_data["input_metrics"]})
        if temp_data["powershare"]: final_output_list.append({**base_info, "data_type": "pdu_powershare_metrics", **temp_data["powershare"]})
        if temp_data["global_metrics"]: final_output_list.append({**base_info, "data_type": "pdu_global_metrics", **temp_data["global_metrics"]})
        
        for index, metrics in temp_data["breakers"].items(): final_output_list.append({**base_info, "data_type": "pdu_breaker_metrics", "breaker_index": index, **metrics})
        for index, metrics in temp_data["phases"].items(): final_output_list.append({**base_info, "data_type": "pdu_phase_metrics", "phase_index": index, **metrics})
        for index, metrics in temp_data["outlets"].items(): final_output_list.append({**base_info, "data_type": "pdu_outlet_metrics", "outlet_index": index, **metrics})
        for index, metrics in temp_data["hids"].items(): final_output_list.append({**base_info, "data_type": "pdu_hid_metrics", "hid_index": index, **metrics})
        for sensor_type, indexes in temp_data["sensors"].items():
            for index, metrics in indexes.items():
                sensor_id = f"{sensor_type}_{index}"
                final_output_list.append({**base_info, "data_type": f"pdu_{sensor_type.lower()}_sensor_metrics", "sensor_id": sensor_id, **metrics})

    print(f"İşlem tamamlandı. {len(final_output_list)} adet yapılandırılmış kayıt oluşturuldu.", file=sys.stderr)
    return final_output_list

def main():
    parser = argparse.ArgumentParser(description="Zabbix API'den PDU verilerini çeker, işler ve hedeflenen dikey JSON formatında sunar.")
    parser.add_argument('--server', required=True, help='Zabbix sunucusunun IP adresi veya hostname\'i.')
    parser.add_argument('--user', required=True, help='Zabbix API kullanıcı adı.')
    parser.add_argument('--groupid', required=True, help='Verilerin çekileceği host grubunun ID\'si.')
    parser.add_argument('--password', help='Zabbix API şifresi. Belirtilmezse, güvenli bir şekilde sorulur.')
    parser.add_argument('--outfile', help='Çıktının kaydedileceği JSON dosya adı (isteğe bağlı).')
    args = parser.parse_args()

    password = args.password or getpass("Lütfen Zabbix API şifresini girin: ")
    zabbix_client = ZabbixAPIClient(hostname=args.server, username=args.user, password=password)
    try:
        zabbix_client.login()
        raw_data = zabbix_client.get_data_for_group(args.groupid)
    finally:
        zabbix_client.logout()

    if not raw_data:
        print("Belirtilen grupta veri bulunamadı. İşlem sonlandırılıyor.", file=sys.stderr)
        return

    final_data = transform_data(raw_data)
    json_output = json.dumps(final_data, indent=4, ensure_ascii=False)
    
    print(json_output) # stdout

    if args.outfile:
        print(f"\nÇıktı '{args.outfile}' dosyasına kaydediliyor...", file=sys.stderr)
        try:
            with open(args.outfile, 'w', encoding='utf-8') as f: f.write(json_output)
            print("Dosyaya kaydetme işlemi başarılı.", file=sys.stderr)
        except IOError as e:
            print(f"HATA: Dosya yazılamadı. {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
