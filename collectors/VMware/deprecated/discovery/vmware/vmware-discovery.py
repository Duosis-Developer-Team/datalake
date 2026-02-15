#!/usr/bin/env python3

"""
VMware vSphere Discovery Script (Inventory-Only) - v2

Bu script, bir vCenter sunucusuna bağlanarak Datacenter, Cluster, Host ve VM
katmanlarındaki envanteri keşfeder. Metrik toplamaz.

LLD standartlarına uygun olarak, her nesnenin anlık durumunu ('active'/'passive'),
durum açıklamasını ve hiyerarşik ilişkisini (parent/child) raporlar.

Sürüm 2 Değişiklikleri:
- Datacenter altındaki (hostFolder, vmFolder) hiyerarşik keşif düzeltildi.
- vCenter kaydına 'vcenter_hostname' alanı eklendi.
- vCenter 'component_moid' alanı statik "vcenter-self" yerine "vcenter-[ip]"
  olarak dinamikleştirildi.
"""

import sys
import argparse
import json
import ssl
import socket
from datetime import datetime, timezone

# pyVmomi kütüphanelerini import et
try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim, vmodl
except ImportError:
    print(
        "Hata: pyVmomi kütüphanesi bulunamadı. "
        "Lütfen 'pip install pyvmomi' komutu ile kurun.",
        file=sys.stderr
    )
    sys.exit(1)

# Tüm çalıştırma için tek bir global zaman damgası (LLD Standardı)
COLLECTION_TIMESTAMP = datetime.now(timezone.utc).isoformat()


def parse_args():
    """Komut satırı argümanlarını alır."""
    parser = argparse.ArgumentParser(
        description='VMware vSphere Discovery Script v2'
    )
    parser.add_argument(
        '--ip',
        required=True,
        help='vCenter sunucusunun IP adresi veya FQDN.'
    )
    parser.add_argument(
        '--user',
        required=True,
        help='vCenter kullanıcı adı (örn: administrator@vsphere.local)'
    )
    parser.add_argument(
        '--pass',
        required=True,
        dest='password',
        help='vCenter şifresi.'
    )
    return parser.parse_args()


def pre_flight_check(ip, port, timeout=5.0):
    """
    SmartConnect'ten önce vCenter portunu (genellikle 443) kontrol eder.
    Bu, 'port couldn't be reached' hatasını yakalamak içindir.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        if result == 0:
            return True, "Port 443 check successful."
        else:
            return False, f"Could not reach {ip} on port {port}. Connection refused or timed out."
    except socket.gaierror:
        return False, f"Could not resolve hostname: {ip}"
    except Exception as e:
        return False, f"Port check failed with error: {str(e)}"
    finally:
        sock.close()


def get_hostname(ip):
    """Verilen IP için FQDN/Hostname çözmeye çalışır."""
    try:
        fqdn = socket.getfqdn(ip)
        return fqdn
    except Exception:
        return None # Çözemezse None döner


def create_vcenter_record(ip, hostname, uuid, status, desc, version=None):
    """vCenter'ın kendisi için standart bir kayıt oluşturur."""
    
    # component_moid'yi LLD standardına uygun ve IP'ye özel hale getir
    vcenter_moid = f"vcenter-{ip}"
    
    return {
        "collection_timestamp": COLLECTION_TIMESTAMP,
        "vcenter_uuid": uuid,
        "vcenter_ip": ip,
        "vcenter_hostname": hostname,
        "data_type": "vmware_inventory_vcenter",
        "component_moid": vcenter_moid,
        "parent_component_moid": None, # vCenter kök nesnedir
        "component_uuid": None,
        "name": hostname if hostname else ip, # İsim olarak hostname'i tercih et
        "status": status,
        "status_description": desc,
        "version": version
    }


def get_standard_status(obj):
    """
    Bir VMware nesnesini 'active'/'passive' durum modeline çevirir.
    """
    try:
        if isinstance(obj, vim.VirtualMachine):
            state = obj.runtime.powerState
            if state == 'poweredOn':
                return 'active', 'VM is powered on.'
            elif state == 'poweredOff':
                return 'passive', 'VM is powered off.'
            elif state == 'suspended':
                return 'passive', 'VM is suspended.'
        
        elif isinstance(obj, vim.HostSystem):
            state = obj.runtime.connectionState
            if state == 'connected' and not obj.runtime.inMaintenanceMode:
                return 'active', 'Host is connected and not in maintenance mode.'
            elif obj.runtime.inMaintenanceMode:
                return 'passive', 'Host is in maintenance mode.'
            elif state == 'disconnected':
                return 'passive', 'Host is disconnected from vCenter.'
            elif state == 'notResponding':
                return 'passive', 'Host is not responding.'
        
        elif isinstance(obj, vim.ClusterComputeResource):
            status = obj.summary.overallStatus
            if status == 'green' or status == 'gray':
                return 'active', f'Cluster status is {status}.'
            elif status == 'yellow':
                return 'passive', 'Cluster status is yellow (warning).'
            elif status == 'red':
                return 'passive', 'Cluster status is red (alarm).'

        elif isinstance(obj, vim.Datacenter):
            # Datacenter'lar vCenter'a bağlı olduğu sürece aktiftir
            return 'active', 'Datacenter is accessible.'

    except Exception as e:
        return 'passive', f'Could not determine status. Error: {str(e)}'

    # Bilinmeyen veya durumu önemsiz nesneler
    return 'unknown', 'Status tracking not implemented for this object type.'


def create_record_for_object(obj, parent_moid, vcenter_uuid):
    """
    Bir vCenter nesnesi için standart JSON kaydını oluşturur ve
    zenginleştirir.
    """
    
    # İlgilenmediğimiz nesne tiplerini atla (ResourcePool, Network, vb.)
    if not isinstance(obj, (
        vim.Datacenter, 
        vim.ClusterComputeResource, 
        vim.HostSystem, 
        vim.VirtualMachine
    )):
        return None

    # VM template'lerini atla
    if isinstance(obj, vim.VirtualMachine) and obj.config.template:
        return None

    status, status_desc = get_standard_status(obj)

    # LLD Standart Anahtarları
    record = {
        "collection_timestamp": COLLECTION_TIMESTAMP,
        "vcenter_uuid": vcenter_uuid,
        "parent_component_moid": parent_moid, # Hiyerarşik İlişki
        "component_moid": obj._moId,
        "status": status,
        "status_description": status_desc,
        "component_uuid": None, # Varsayılan
        "name": obj.name
    }

    # Tipe Göre Zenginleştirme
    if isinstance(obj, vim.Datacenter):
        record['data_type'] = 'vmware_inventory_datacenter'

    elif isinstance(obj, vim.ClusterComputeResource):
        record['data_type'] = 'vmware_inventory_cluster'
    
    elif isinstance(obj, vim.HostSystem):
        record['data_type'] = 'vmware_inventory_host'
        record['component_uuid'] = obj.hardware.systemInfo.uuid # ESXi BIOS UUID
        record['model'] = obj.hardware.systemInfo.model
        record['version'] = obj.config.product.version
        record['build'] = obj.config.product.build

    elif isinstance(obj, vim.VirtualMachine):
        record['data_type'] = 'vmware_inventory_vm'
        record['component_uuid'] = obj.config.uuid # VM Instance UUID
        record['guest_os'] = obj.config.guestFullName
        try:
            record['tools_status'] = obj.guest.toolsStatus
        except Exception:
            record['tools_status'] = 'unknown' # Bazen guest bilgisi gelmeyebilir

    return record


def discover_children(current_obj, parent_moid, vcenter_uuid, data_list):
    """
    vCenter envanter ağacında özyineli (recursive) olarak gezer.
    (Düzeltilmiş Hiyerarşi Mantığı)
    """
    
    # 1. Bu nesne için bir kayıt oluştur (veya atla)
    record = create_record_for_object(current_obj, parent_moid, vcenter_uuid)
    
    current_parent_moid = parent_moid # Eğer bu nesne atlanırsa, parent değişmez
    if record:
        data_list.append(record)
        current_parent_moid = record['component_moid'] # Yeni parent bu nesne
    
    # 2. Alt nesneleri (children) bul (DÜZELTİLMİŞ MANTIK)
    children_to_scan = []
    if hasattr(current_obj, 'childEntity'): # Folder
        children_to_scan.extend(current_obj.childEntity)
    
    # Datacenter: hostFolder ve vmFolder'ın *içine* bak
    if hasattr(current_obj, 'hostFolder') and hasattr(current_obj.hostFolder, 'childEntity'):
        children_to_scan.extend(current_obj.hostFolder.childEntity)
    if hasattr(current_obj, 'vmFolder') and hasattr(current_obj.vmFolder, 'childEntity'):
        children_to_scan.extend(current_obj.vmFolder.childEntity)

    # Cluster: 'host' listesine bak
    if hasattr(current_obj, 'host'): 
        children_to_scan.extend(current_obj.host)
    
    # Host: 'vm' listesine bak
    if hasattr(current_obj, 'vm'): 
        children_to_scan.extend(current_obj.vm)

    # 3. Özyineli olarak devam et
    for child in children_to_scan:
        discover_children(child, current_parent_moid, vcenter_uuid, data_list)


def main():
    """Ana script fonksiyonu."""
    args = parse_args()
    master_data_list = []
    si = None
    vcenter_uuid = None
    vcenter_hostname = get_hostname(args.ip) # Hostname'i çözmeyi dene

    # Adım 1: Bağlantı Öncesi Port Kontrolü
    port_check_ok, port_error_msg = pre_flight_check(args.ip, 443)
    
    if not port_check_ok:
        # vCenter'a erişilemiyorsa, pasif bir vCenter kaydı oluştur ve çık.
        record = create_vcenter_record(
            args.ip, 
            vcenter_hostname,
            None, 
            'passive', 
            port_error_msg
        )
        master_data_list.append(record)
        print(json.dumps(master_data_list, indent=2))
        sys.exit(1) # Hata ile çıkış yap

    # Adım 2: vCenter Bağlantı Denemesi
    try:
        # SSL sertifika doğrulaması olmadan bağlan (unverified context)
        context = ssl._create_unverified_context()
        si = SmartConnect(
            host=args.ip,
            user=args.user,
            pwd=args.password,
            sslContext=context
        )
        
        content = si.RetrieveContent()
        vcenter_uuid = content.about.instanceUuid
        
        # vCenter için 'active' kayıt oluştur
        active_desc = f"Connection successful. vCenter Server {content.about.version}"
        record = create_vcenter_record(
            args.ip, 
            vcenter_hostname,
            vcenter_uuid, 
            'active', 
            active_desc,
            content.about.version
        )
        master_data_list.append(record)

        # Adım 3: Hiyerarşik Keşfi Başlat
        # Kök klasörden başlıyoruz, parent'ı vCenter'ın kendisidir.
        root_folder = content.rootFolder
        vcenter_moid = record['component_moid'] # (örn: "vcenter-10.132.2.184")
        
        # rootFolder'ın kendisi bir kayıt oluşturmaz (create_record_for_object 
        # onu atlar), ancak alt öğeleri (Datacenter'lar) için 
        # özyineli taramayı başlatırız.
        discover_children(
            root_folder, 
            vcenter_moid, 
            vcenter_uuid, 
            master_data_list
        )

    except vim.fault.InvalidLogin:
        # Adım 2.1: Credential Hatası
        err_msg = "Failed to connect: Invalid username or password."
        record = create_vcenter_record(args.ip, vcenter_hostname, None, 'passive', err_msg)
        master_data_list.append(record)

    except ConnectionRefusedError:
        # Adım 2.2: Bağlantı reddedildi (Port check sonrası olabilir)
        err_msg = "Connection refused by server. Service might be down."
        record = create_vcenter_record(args.ip, vcenter_hostname, None, 'passive', err_msg)
        master_data_list.append(record)
        
    except Exception as e:
        # Adım 2.3: Diğer tüm beklenmedik hatalar
        err_msg = f"An unexpected error occurred: {str(e)}"
        record = create_vcenter_record(args.ip, vcenter_hostname, vcenter_uuid, 'passive', err_msg)
        master_data_list.append(record)

    finally:
        # Adım 4: Bağlantıyı Kapat ve Çıktıyı Bas
        if si:
            Disconnect(si)
        
        # LLD Standardı: Tüm sonuçları tek bir JSON dizisi olarak stdout'a bas.
        print(json.dumps(master_data_list, indent=2))


if __name__ == "__main__":
    main()