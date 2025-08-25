# -*- coding: utf-8 -*-
"""
Brocade Fabric OS REST API Collector (FOS 8.x - Final Version)

Sürüm 14 Değişiklikleri:
- API'dan gelen tüm JSON verilerindeki anahtar adlarında bulunan tire (-) karakterlerini
  otomatik olarak alt tire (_) karakterine çeviren bir fonksiyon eklendi.
- port_type alanı, veri tipi tutarlılığı için her zaman metin (string) olarak işlenir.
- Bu değişiklikler, JSON çıktısının, Avro şemasının ve veritabanı tablolarının
  birbiriyle tam uyumlu olmasını sağlar ve hem NULL değer hem de veri tipi hatalarını çözer.
"""
import requests
import json
import os
import sys
import argparse
from datetime import datetime

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def log_stderr(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", file=sys.stderr)

def sanitize_keys(obj):
    if isinstance(obj, dict):
        return {key.replace('-', '_'): sanitize_keys(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [sanitize_keys(element) for element in obj]
    return obj

class BrocadeRestCollector:
    def __init__(self, host, username, password, snapshot_file):
        self.host_arg = host
        self.base_url = f"http://{host}"
        self.auth_info = (username, password)
        self.session = requests.Session()
        self.headers = {
            'Accept': 'application/yang-data+json',
            'Content-Type': 'application/yang-data+json'
        }
        self.snapshot_file = snapshot_file
        self.collection_timestamp = datetime.now().isoformat()
        self.switch_name = host
        log_stderr(f"Kolektör başlatıldı. Hedef: {self.base_url}")

    def login(self):
        log_stderr("Oturum açılıyor...")
        login_url = f"{self.base_url}/rest/login"
        try:
            response = self.session.post(login_url, auth=self.auth_info)
            response.raise_for_status()
            auth_header = response.headers.get('Authorization')
            if not auth_header:
                raise ConnectionError("Giriş başarılı ancak Yetkilendirme başlığı alınamadı.")
            self.headers['Authorization'] = auth_header
            log_stderr("Oturum başarıyla açıldı.")
            return True
        except requests.exceptions.RequestException as e:
            log_stderr(f"HATA: Oturum açılamadı. {e}")
            return False

    def logout(self):
        log_stderr("Oturum kapatılıyor...")
        logout_url = f"{self.base_url}/rest/logout"
        try:
            if 'Authorization' in self.headers:
                self.session.post(logout_url, headers={'Authorization': self.headers['Authorization']})
                log_stderr("Oturum başarıyla kapatıldı.")
        except requests.exceptions.RequestException as e:
            log_stderr(f"UYARI: Oturum kapatılamadı. {e}")

    def _get_api_data(self, endpoint):
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log_stderr(f"HATA: Endpoint'ten veri alınamadı: {endpoint}. Hata: {e}")
            return None
        except json.JSONDecodeError:
            log_stderr(f"HATA: Geçersiz JSON yanıtı alındı: {endpoint}")
            return None

    def get_switch_details(self):
        log_stderr("Switch detayları (isim) alınıyor...")
        endpoint = "/rest/running/brocade-fibrechannel-switch/fibrechannel-switch"
        data = self._get_api_data(endpoint)
        try:
            switch_info = data['Response']['fibrechannel-switch']
            if isinstance(switch_info, list):
                switch_info = switch_info[0]
            switch_name_from_api = switch_info.get('user-friendly-name')
            if switch_name_from_api:
                self.switch_name = switch_name_from_api
                log_stderr(f"Switch adı başarıyla alındı: {self.switch_name}")
            else:
                log_stderr("UYARI: Switch için 'user-friendly-name' bulunamadı.")
        except (TypeError, KeyError, IndexError):
            log_stderr("UYARI: Switch adı alınamadı. Argüman değeri kullanılacak.")

    def get_port_status_info(self):
        log_stderr("Port durum bilgileri toplanıyor...")
        endpoint = "/rest/running/brocade-interface/fibrechannel"
        data = self._get_api_data(endpoint)
        if not data or 'Response' not in data or 'fibrechannel' not in data['Response']:
            log_stderr("Port durum bilgileri alınamadı.")
            return []
        port_list = data['Response']['fibrechannel']
        if not isinstance(port_list, list):
            port_list = [port_list]
        processed_statuses = []
        for port_data in port_list:
            clean_port_data = sanitize_keys(port_data)
            clean_port_data['switch_host'] = self.switch_name
            clean_port_data['data_type'] = "port_status"
            clean_port_data['collection_timestamp'] = self.collection_timestamp
            neighbor_info = clean_port_data.pop('neighbor', {})
            if neighbor_info and 'wwn' in neighbor_info and isinstance(neighbor_info['wwn'], list):
                clean_port_data['neighbor_wwns'] = ','.join(neighbor_info['wwn'])
            else:
                clean_port_data['neighbor_wwns'] = None
            processed_statuses.append(clean_port_data)
        log_stderr(f"{len(processed_statuses)} port için durum bilgisi toplandı.")
        return processed_statuses

    def get_all_port_stats(self):
        log_stderr("Port istatistikleri toplanıyor...")
        endpoint = "/rest/running/brocade-interface/fibrechannel-statistics"
        data = self._get_api_data(endpoint)
        if not data or 'Response' not in data or 'fibrechannel-statistics' not in data['Response']:
            log_stderr("Port istatistikleri alınamadı.")
            return {}
        stats_by_port = {}
        stats_list = data['Response']['fibrechannel-statistics']
        if not isinstance(stats_list, list):
            stats_list = [stats_list]
        for stat in stats_list:
            port_name = stat.get('name')
            if port_name:
                stats_by_port[port_name] = sanitize_keys(stat)
        log_stderr(f"{len(stats_by_port)} port için istatistik toplandı.")
        return stats_by_port

    def get_name_server_info(self):
        log_stderr("Name Server bilgileri toplanıyor...")
        endpoint = "/rest/running/brocade-name-server/fibrechannel-name-server"
        data = self._get_api_data(endpoint)
        if not data or 'Response' not in data or 'fibrechannel-name-server' not in data['Response']:
            log_stderr("Name server bilgisi alınamadı.")
            return []
        processed_entries = []
        ns_entries = data['Response']['fibrechannel-name-server']
        if not isinstance(ns_entries, list):
            ns_entries = [ns_entries]
        for entry in ns_entries:
            clean_entry = sanitize_keys(entry)
            processed_entries.append({
                "switch_host": self.switch_name,
                "data_type": "fabric_device_entry",
                "collection_timestamp": self.collection_timestamp,
                "device_wwpn": clean_entry.get("port_name"),
                "device_wwnn": clean_entry.get("node_name"),
                "port_index": clean_entry.get("port_index"),
                "port_id": clean_entry.get("port_id"),
                "port_symbolic_name": clean_entry.get("port_symbolic_name"),
                "node_symbolic_name": clean_entry.get("node_symbolic_name"),
                "device_port_type": str(clean_entry.get("port_type")), # Her zaman string olsun
                "class_of_service": clean_entry.get("class_of_service")
            })
        log_stderr(f"{len(processed_entries)} Name Server kaydı işlendi.")
        return processed_entries

    def process_port_statistics(self, new_stats):
        log_stderr("Port istatistikleri işleniyor (delta hesaplaması)...")
        old_stats = {}
        if os.path.exists(self.snapshot_file):
            try:
                with open(self.snapshot_file, 'r') as f:
                    old_data = json.load(f)
                    old_stats = old_data.get('statistics', {})
                    log_stderr(f"Önceki istatistik anlık görüntüsü bulundu: {self.snapshot_file}")
            except Exception as e:
                log_stderr(f"UYARI: Önceki istatistik dosyası okunamadı: {e}")
        processed_stats = []
        cumulative_keys = [
            'in_octets', 'out_octets', 'in_frames', 'out_frames', 'crc_errors', 
            'class_3_discards', 'link_failures', 'loss_of_signal', 'loss_of_sync', 
            'invalid_transmission_words'
        ]
        for port_name, current_port_stats in new_stats.items():
            previous_port_stats = old_stats.get(port_name, {})
            processed_record = current_port_stats.copy()
            processed_record["switch_host"] = self.switch_name
            processed_record["data_type"] = "port_statistics"
            processed_record["collection_timestamp"] = self.collection_timestamp
            time_diff_sec = 0
            if previous_port_stats and 'collection_timestamp' in old_data:
                try:
                    prev_ts = datetime.fromisoformat(old_data['collection_timestamp'])
                    curr_ts = datetime.fromisoformat(self.collection_timestamp)
                    time_diff_sec = (curr_ts - prev_ts).total_seconds()
                except Exception: pass
            processed_record["time_difference_seconds"] = round(time_diff_sec, 2)
            for key in cumulative_keys:
                new_val = current_port_stats.get(key)
                old_val = previous_port_stats.get(key)
                try:
                    new_val = int(new_val) if new_val is not None else 0
                    old_val = int(old_val) if old_val is not None else 0
                    delta_key = f"{key}_delta"
                    if previous_port_stats and new_val >= old_val:
                        processed_record[delta_key] = new_val - old_val
                    else:
                        processed_record[delta_key] = 0
                except Exception: pass
            processed_stats.append(processed_record)
        log_stderr(f"{len(processed_stats)} port için istatistikler işlendi.")
        return processed_stats

    def _save_snapshot(self, data):
        log_stderr(f"Anlık görüntü dosyası yazılıyor: {self.snapshot_file}")
        try:
            with open(self.snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            log_stderr("Yazma işlemi başarılı.")
        except IOError as e:
            log_stderr(f"HATA: Anlık görüntü dosyası yazılamadı: {self.snapshot_file}. Hata: {e}")

    def run(self):
        if not self.login():
            sys.exit(1)
        self.get_switch_details()
        final_output_data = []
        port_status_data = self.get_port_status_info()
        if port_status_data: final_output_data.extend(port_status_data)
        name_server_data = self.get_name_server_info()
        if name_server_data: final_output_data.extend(name_server_data)
        new_stats = self.get_all_port_stats()
        if new_stats:
            processed_stats = self.process_port_statistics(new_stats)
            if processed_stats: final_output_data.extend(processed_stats)
            snapshot_data = {"collection_timestamp": self.collection_timestamp, "statistics": new_stats}
            self._save_snapshot(snapshot_data)
        if final_output_data:
            try:
                json.dump(final_output_data, sys.stdout, indent=4, ensure_ascii=False)
            except Exception as e:
                log_stderr(f"HATA: Nihai çıktı stdout'a yazılamadı. Hata: {e}")
        else:
            log_stderr("UYARI: Kaydedilecek işlenmiş veri bulunamadı.")
        self.logout()

def main():
    parser = argparse.ArgumentParser(description="Brocade REST API Collector (FOS 8.x)")
    parser.add_argument('--host', required=True, help="Brocade anahtarının IP adresi veya FQDN'i.")
    parser.add_argument('--username', required=True, help="REST API için kullanıcı adı.")
    parser.add_argument('--password', required=True, help="REST API için şifre.")
    args = parser.parse_args()
    safe_host_filename = args.host.replace('.', '_').replace(':', '_')
    snapshot_file = f'brocade_stats_snapshot_{safe_host_filename}.json'
    collector = BrocadeRestCollector(args.host, args.username, args.password, snapshot_file)
    collector.run()

if __name__ == "__main__":
    main()