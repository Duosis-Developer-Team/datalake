import requests
import json
import argparse
import sys
from datetime import datetime, timezone
import warnings

# Self-signed sertifikalar için gelen uyarıları bastır
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def create_session(host, username, password):
    """Redfish servisinde bir oturum oluşturur ve session token'ı döndürür."""
    session_url = f"https://{host}/redfish/v1/SessionService/Sessions"
    payload = {"UserName": username, "Password": password}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(session_url, json=payload, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        session_token = response.headers.get('X-Auth-Token')
        session_location = response.headers.get('Location')
        if not session_token or not session_location:
            print("Hata: Oturum token'ı veya lokasyonu alınamadı.", file=sys.stderr)
            return None, None
        print(f"Başarıyla oturum açıldı. Session URI: {session_location}", file=sys.stderr)
        return session_token, session_location
    except requests.exceptions.RequestException as e:
        print(f"Hata: Oturum açılırken bir sorun oluştu: {e}", file=sys.stderr)
        return None, None

def close_session(host, session_token, session_location):
    """Açık olan Redfish oturumunu kapatır."""
    if not session_token or not session_location:
        return
    headers = {'X-Auth-Token': session_token}
    if session_location.startswith('http'):
        session_url = session_location
    else:
        session_url = f"https://{host}{session_location}"
    try:
        requests.delete(session_url, headers=headers, verify=False, timeout=10)
        print("Oturum başarıyla kapatıldı.", file=sys.stderr)
    except requests.exceptions.RequestException as e:
        print(f"Hata: Oturum kapatılırken bir sorun oluştu: {e}", file=sys.stderr)

def get_data(url, headers):
    """Verilen URL'den Redfish verisini çeker."""
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Hata: Veri çekilemedi: {url} - {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="HPE iLO'dan Redfish API ile kapsamlı veri topla.")
    parser.add_argument('--host', required=True, help="iLO IP adresi veya FQDN")
    parser.add_argument('--username', required=True, help="iLO kullanıcı adı")
    parser.add_argument('--password', required=True, help="iLO şifresi")
    args = parser.parse_args()

    session_token, session_location = create_session(args.host, args.username, args.password)
    if not session_token:
        sys.exit(1)

    auth_headers = {'X-Auth-Token': session_token}
    base_url = f"https://{args.host}"
    all_data = []
    collection_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')

    try:
        # --- ANA VERİLERİ ÇEKME ---
        system_data = get_data(f"{base_url}/redfish/v1/Systems/1/", auth_headers)
        chassis_data = get_data(f"{base_url}/redfish/v1/Chassis/1/", auth_headers)
        power_data = get_data(f"{base_url}/redfish/v1/Chassis/1/Power/", auth_headers)
        thermal_data = get_data(f"{base_url}/redfish/v1/Chassis/1/Thermal/", auth_headers)
        
        if not system_data or not chassis_data:
            print("Ana sistem veya şasi verisi alınamadı. Betik sonlandırılıyor.", file=sys.stderr)
            return

        chassis_serial = chassis_data.get("SerialNumber")

        # --- BÖLÜM 1: ENVANTER VERİLERİ ---

        # 1.1 Ana Envanter
        if chassis_data and system_data:
            processor_summary = system_data.get('ProcessorSummary', {})
            memory_summary = system_data.get('MemorySummary', {})
            all_data.append({
                "data_type": "inventory", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial,
                "chassis_model": chassis_data.get("Model"), "chassis_manufacturer": chassis_data.get("Manufacturer"),
                "system_hostname": system_data.get("HostName"), "system_power_state": system_data.get("PowerState"),
                "processor_count": processor_summary.get("Count"), "processor_model": processor_summary.get("Model"),
                "processor_status_health": processor_summary.get('Status', {}).get('HealthRollup'),
                "total_system_memory_gib": memory_summary.get("TotalSystemMemoryGiB"),
                "memory_status_health": memory_summary.get('Status', {}).get('HealthRollup')
            })

        # 1.2 İşlemci (CPU) Envanteri
        processors_link = system_data.get('Processors', {}).get('@odata.id')
        if processors_link and (proc_coll := get_data(f"{base_url}{processors_link}", auth_headers)):
            for member in proc_coll.get('Members', []):
                if (proc_url := member.get('@odata.id')) and (proc_detail := get_data(f"{base_url}{proc_url}", auth_headers)):
                    all_data.append({"data_type": "inventory_processor", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "processor_id": proc_detail.get("Id"), "model": proc_detail.get("Model"), "max_speed_mhz": proc_detail.get("MaxSpeedMHz"), "total_cores": proc_detail.get("TotalCores"), "total_threads": proc_detail.get("TotalThreads"), "status_health": proc_detail.get("Status", {}).get("Health"), "status_state": proc_detail.get("Status", {}).get("State")})

        # 1.3 Bellek (Memory) Envanteri
        memory_link = system_data.get('Memory', {}).get('@odata.id')
        if memory_link and (mem_coll := get_data(f"{base_url}{memory_link}", auth_headers)):
            for member in mem_coll.get('Members', []):
                if (mem_url := member.get('@odata.id')) and (mem_detail := get_data(f"{base_url}{mem_url}", auth_headers)):
                    all_data.append({"data_type": "inventory_memory", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "dimm_id": mem_detail.get("Id"), "memory_type": mem_detail.get("MemoryType"), "capacity_mib": mem_detail.get("CapacityMiB"), "operating_speed_mhz": mem_detail.get("OperatingSpeedMhz"), "manufacturer": mem_detail.get("Manufacturer"), "part_number": mem_detail.get("PartNumber"), "status_health": mem_detail.get("Status", {}).get("Health"), "status_state": mem_detail.get("Status", {}).get("State")})
        
        # 1.4 Depolama (Disk) Envanteri ve Metrikleri
        smart_storage_link = system_data.get('Oem', {}).get('Hpe', {}).get('Links', {}).get('SmartStorage', {}).get('@odata.id')
        if smart_storage_link and (storage_system := get_data(f"{base_url}{smart_storage_link}", auth_headers)):
            array_controllers_link = storage_system.get('Links', {}).get('ArrayControllers', {}).get('@odata.id')
            if array_controllers_link and (ac_coll := get_data(f"{base_url}{array_controllers_link}", auth_headers)):
                for member in ac_coll.get('Members', []):
                    if (ctrl_url := member.get('@odata.id')) and (ctrl_detail := get_data(f"{base_url}{ctrl_url}", auth_headers)):
                        physical_drives_link = ctrl_detail.get('Links', {}).get('PhysicalDrives', {}).get('@odata.id')
                        if physical_drives_link and (drive_coll := get_data(f"{base_url}{physical_drives_link}", auth_headers)):
                            for drive_member in drive_coll.get('Members', []):
                                if (drive_url := drive_member.get('@odata.id')) and (drive_detail := get_data(f"{base_url}{drive_url}", auth_headers)):
                                    capacity_mib = drive_detail.get("CapacityMiB")
                                    capacity_bytes_val = capacity_mib * 1024 * 1024 if capacity_mib is not None else None
                                    
                                    # Envanter Kaydı
                                    all_data.append({
                                        "data_type": "inventory_disk", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, 
                                        "disk_id": drive_detail.get("Id"), "model": drive_detail.get("Model"), 
                                        "capacity_bytes": capacity_bytes_val, "protocol": drive_detail.get("InterfaceType"), 
                                        "media_type": drive_detail.get("MediaType"), "serial_number": drive_detail.get("SerialNumber"),
                                        "firmware_version": drive_detail.get("FirmwareVersion", {}).get("Current", {}).get("VersionString"),
                                        "block_size_bytes": drive_detail.get("BlockSizeBytes"),
                                        "status_health": drive_detail.get("Status", {}).get("Health"), 
                                        "status_state": drive_detail.get("Status", {}).get("State")
                                    })

                                    # DÜZELTME: Disk metrikleri burada, envanterle birlikte toplanıyor
                                    all_data.append({
                                        "data_type": "metric_disk",
                                        "collection_timestamp": collection_time,
                                        "chassis_serial_number": chassis_serial,
                                        "disk_id": drive_detail.get("Id"),
                                        "power_on_hours": drive_detail.get("PowerOnHours"),
                                        "temperature_celsius": drive_detail.get("CurrentTemperatureCelsius"),
                                        "endurance_utilization_percent": drive_detail.get("SSDEnduranceUtilizationPercentage")
                                    })

        # 1.5 Güç Kaynağı (PSU) Envanteri
        if power_data and "PowerSupplies" in power_data:
            for psu in power_data.get("PowerSupplies", []):
                if psu.get("Status", {}).get("State") == "Enabled":
                    try:
                        psu_id_int = int(psu.get("MemberId"))
                        all_data.append({"data_type": "inventory_psu", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "psu_id": psu_id_int, "model": psu.get("Model"), "serial_number": psu.get("SerialNumber"), "part_number": psu.get("SparePartNumber"), "firmware_version": psu.get("FirmwareVersion"), "power_capacity_watts": psu.get("PowerCapacityWatts"), "status_health": psu.get("Status", {}).get("Health")})
                    except (ValueError, TypeError):
                        print(f"Uyarı: Geçersiz psu_id değeri '{psu.get('MemberId')}' atlanıyor (envanter).", file=sys.stderr)

        # 1.6 Ağ Arayüzü (NIC) Envanteri
        nic_collection_url = system_data.get('EthernetInterfaces', {}).get('@odata.id')
        if nic_collection_url and (nic_collection := get_data(f"{base_url}{nic_collection_url}", auth_headers)):
            for member in nic_collection.get('Members', []):
                if (nic_url := member.get('@odata.id')) and (nic_detail := get_data(f"{base_url}{nic_url}", auth_headers)):
                    all_data.append({"data_type": "inventory_nic", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "interface_id": nic_detail.get("Id"), "name": nic_detail.get("Name"), "mac_address": nic_detail.get("MACAddress"), "speed_mbps": nic_detail.get("SpeedMbps"), "link_status": nic_detail.get("LinkStatus"), "full_duplex": nic_detail.get("FullDuplex"), "ipv4_addresses": json.dumps(nic_detail.get("IPv4Addresses")), "status_health": nic_detail.get("Status", {}).get("Health")})

        # 1.7 BIOS Ayarları Envanteri
        bios_url = system_data.get('Bios', {}).get('@odata.id')
        if bios_url and (bios_data := get_data(f"{base_url}{bios_url}", auth_headers)):
            if bios_attributes := bios_data.get("Attributes", {}):
                key_bios_settings = ["WorkloadProfile", "ProcHyperthreading", "ProcVirtualization", "PowerRegulator", "Sriov", "BootMode"]
                bios_record = {"data_type": "inventory_bios", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial}
                for key in key_bios_settings:
                    bios_record[key.lower()] = bios_attributes.get(key)
                all_data.append(bios_record)

        # 1.8 Firmware Envanteri
        fw_inventory_url = f"{base_url}/redfish/v1/UpdateService/FirmwareInventory/"
        if fw_inventory_url and (fw_collection := get_data(fw_inventory_url, auth_headers)):
            for member in fw_collection.get('Members', []):
                if (fw_url := member.get('@odata.id')) and (fw_detail := get_data(f"{base_url}{fw_url}", auth_headers)):
                    all_data.append({
                        "data_type": "inventory_firmware",
                        "collection_timestamp": collection_time,
                        "chassis_serial_number": chassis_serial,
                        "component_name": fw_detail.get("Name"),
                        "version": fw_detail.get("Version"),
                        "updateable": fw_detail.get("Updateable"),
                        "device_context": fw_detail.get("Oem", {}).get("Hpe", {}).get("DeviceContext")
                    })

        # --- BÖLÜM 2: METRİK VERİLERİ (GENİŞ FORMATTA) ---

        # 2.1 Genel Sistem Metrikleri
        system_usage = system_data.get('Oem', {}).get('Hpe', {}).get('SystemUsage', {})
        if system_usage:
            all_data.append({"data_type": "metric_system", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "cpu_utilization_percent": system_usage.get("CPUUtil"), "memory_bus_utilization_percent": system_usage.get("MemoryBusUtil")})

        # 2.2 CPU Metrikleri
        if system_usage:
            processor_count = system_data.get("ProcessorSummary", {}).get("Count", 0)
            for i in range(processor_count):
                cpu_id = i + 1
                all_data.append({"data_type": "metric_cpu", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "cpu_id": cpu_id, "power_watts": system_usage.get(f"CPU{i}Power"), "frequency_mhz": system_usage.get(f"AvgCPU{i}Freq")})
        
        # 2.3 Termal Metrikler
        if thermal_data:
            for sensor in thermal_data.get("Temperatures", []):
                if sensor.get("Status", {}).get("State") == "Enabled":
                    all_data.append({"data_type": "metric_temperature", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "sensor_name": sensor.get("Name"), "reading_celsius": sensor.get("ReadingCelsius"), "status_health": sensor.get("Status", {}).get("Health")})
            for fan in thermal_data.get("Fans", []):
                if fan.get("Status", {}).get("State") == "Enabled":
                    all_data.append({"data_type": "metric_fan", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "fan_name": fan.get("Name"), "reading_percent": fan.get("Reading"), "reading_units": fan.get("ReadingUnits"), "status_health": fan.get("Status", {}).get("Health")})

        # 2.4 Güç Kaynağı Metrikleri
        if power_data and "PowerSupplies" in power_data:
            for psu in power_data.get("PowerSupplies", []):
                if psu.get("Status", {}).get("State") == "Enabled" and psu.get("LastPowerOutputWatts") is not None:
                    try:
                        psu_id_int = int(psu.get("MemberId"))
                        all_data.append({"data_type": "metric_power", "collection_timestamp": collection_time, "chassis_serial_number": chassis_serial, "psu_id": psu_id_int, "power_output_watts": psu.get("LastPowerOutputWatts")})
                    except (ValueError, TypeError):
                        print(f"Uyarı: Geçersiz psu_id değeri '{psu.get('MemberId')}' atlanıyor (metrik).", file=sys.stderr)
        
        print(json.dumps(all_data, indent=4))

    finally:
        close_session(args.host, session_token, session_location)


if __name__ == "__main__":
    main()
