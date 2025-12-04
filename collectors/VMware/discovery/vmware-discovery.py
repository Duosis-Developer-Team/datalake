#!/usr/bin/env python3

"""
VMware vSphere Discovery Script v5 (Host-Centric Only)

Bu script, VM'leri yalnızca fiziksel HOST hiyerarşisi üzerinden keşfeder.
- Folder (Klasör) yapısını görmezden gelir.
- Her VM'in parent'ının kesinlikle bir HostSystem olmasını garanti eder.
- Deduplication otomatik olarak sağlanır (Bir VM sadece bir Host üzerindedir).
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


def parse_args():
    parser = argparse.ArgumentParser(description='VMware Discovery Script v5')
    parser.add_argument('--ip', required=True, help='vCenter IP/FQDN')
    parser.add_argument('--user', required=True, help='User')
    parser.add_argument('--pass', required=True, dest='password', help='Password')
    return parser.parse_args()


def pre_flight_check(ip, port, timeout=5.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        if result == 0: return True, "Port check OK."
        else: return False, f"Could not reach {ip}:{port}."
    except Exception as e: return False, f"Check failed: {str(e)}"
    finally: sock.close()


def get_hostname(ip):
    try:
        fqdn = socket.getfqdn(ip)
        if fqdn == ip: return None
        return fqdn
    except Exception: return None


def create_vcenter_record(ip, hostname, uuid, status, desc, version=None):
    return {
        "vcenter_uuid": uuid,
        "vcenter_ip": ip,
        "vcenter_hostname": hostname,
        "data_type": "vmware_inventory_vcenter",
        "component_moid": f"vcenter-{ip}",
        "component_uuid": None,
        "name": hostname if hostname else ip,
        "status": status,
        "status_description": desc,
        "version": version
    }


def get_standard_status(obj):
    try:
        if isinstance(obj, vim.VirtualMachine):
            if obj.runtime.powerState == 'poweredOn': return 'active', 'VM is powered on.'
            return 'passive', f'VM is {obj.runtime.powerState}.'
        elif isinstance(obj, vim.HostSystem):
            if obj.runtime.connectionState == 'connected' and not obj.runtime.inMaintenanceMode:
                return 'active', 'Host connected.'
            return 'passive', f'Host status: {obj.runtime.connectionState}, Maint: {obj.runtime.inMaintenanceMode}'
        elif isinstance(obj, vim.ClusterComputeResource):
            if obj.summary.overallStatus in ['green', 'gray']: return 'active', 'Cluster OK.'
            return 'passive', f'Cluster status: {obj.summary.overallStatus}'
        elif isinstance(obj, vim.Datacenter):
            return 'active', 'Datacenter OK.'
    except Exception: return 'passive', 'Status unknown'
    return 'unknown', 'N/A'


def create_record(obj, parent_moid, vcenter_uuid):
    """Nesne için kayıt oluşturur."""
    
    # Sadece hedeflediğimiz tipleri işle
    if not isinstance(obj, (vim.Datacenter, vim.ClusterComputeResource, vim.HostSystem, vim.VirtualMachine)):
        return None
    
    # Template'leri atla
    if isinstance(obj, vim.VirtualMachine) and obj.config.template:
        return None

    status, desc = get_standard_status(obj)

    record = {
        "vcenter_uuid": vcenter_uuid,
        "parent_component_moid": parent_moid,
        "component_moid": obj._moId,
        "status": status,
        "status_description": desc,
        "component_uuid": None,
        "name": obj.name
    }

    if isinstance(obj, vim.Datacenter):
        record['data_type'] = 'vmware_inventory_datacenter'
    elif isinstance(obj, vim.ClusterComputeResource):
        record['data_type'] = 'vmware_inventory_cluster'
    elif isinstance(obj, vim.HostSystem):
        record['data_type'] = 'vmware_inventory_host'
        try:
            record['component_uuid'] = obj.hardware.systemInfo.uuid
            record['model'] = obj.hardware.systemInfo.model
        except: 
            record['component_uuid'] = None
            record['model'] = 'Unknown'
        record['version'] = obj.config.product.version
        record['build'] = obj.config.product.build
    elif isinstance(obj, vim.VirtualMachine):
        record['data_type'] = 'vmware_inventory_vm'
        record['component_uuid'] = obj.config.uuid
        record['guest_os'] = obj.config.guestFullName
        try: record['tools_status'] = obj.guest.toolsStatus
        except: record['tools_status'] = 'unknown'

    return record


def discover_host_path_only(current_obj, parent_moid, vcenter_uuid, data_list):
    """
    Sadece HOST yolunu (Compute Resource Path) izleyen tarama.
    VM'leri sadece Host'un altındaysa kaydeder.
    """
    
    # 1. Mevcut nesneyi kaydet
    record = create_record(current_obj, parent_moid, vcenter_uuid)
    
    # Eğer kayıt oluştuysa listeye ekle ve yeni parent bu nesne olsun
    # Eğer oluşmadıysa (örn: Folder), parent değişmeden devam et
    current_parent_moid = parent_moid
    if record:
        data_list.append(record)
        current_parent_moid = record['component_moid']

    # 2. Alt nesneleri bul (SADECE COMPUTE YOLU)
    children_to_scan = []

    # A) Kök veya Folder altındaysak
    if hasattr(current_obj, 'childEntity'):
        # Buradaki her şeye bak (Datacenter olabilir, Folder olabilir)
        children_to_scan.extend(current_obj.childEntity)

    # B) Datacenter altındaysak -> SADECE hostFolder'a gir (vmFolder'a GİRME!)
    if isinstance(current_obj, vim.Datacenter):
        # vmFolder'ı kasıtlı olarak atlıyoruz.
        if hasattr(current_obj, 'hostFolder'):
            # hostFolder bir Folder objesidir, onun içine recursive gireceğiz
            discover_host_path_only(current_obj.hostFolder, current_parent_moid, vcenter_uuid, data_list)
        return # Datacenter'ın childEntity'si yoktur, işimiz bitti.

    # C) Cluster altındaysak -> Hostlara git
    if isinstance(current_obj, vim.ClusterComputeResource):
        if hasattr(current_obj, 'host'):
            children_to_scan.extend(current_obj.host)

    # D) Host altındaysak -> VM'lere git
    if isinstance(current_obj, vim.HostSystem):
        if hasattr(current_obj, 'vm'):
            children_to_scan.extend(current_obj.vm)

    # Alt nesneleri tara
    for child in children_to_scan:
        discover_host_path_only(child, current_parent_moid, vcenter_uuid, data_list)


def main():
    args = parse_args()
    master_data_list = []
    si = None
    vcenter_hostname = get_hostname(args.ip)

    if not pre_flight_check(args.ip, 443)[0]:
        # Erişim yoksa
        record = create_vcenter_record(args.ip, vcenter_hostname, None, 'passive', "Port unreachable")
        print(json.dumps([record], indent=2))
        sys.exit(1)

    try:
        context = ssl._create_unverified_context()
        si = SmartConnect(host=args.ip, user=args.user, pwd=args.password, sslContext=context)
        content = si.RetrieveContent()
        vcenter_uuid = content.about.instanceUuid

        # vCenter Kaydı
        record = create_vcenter_record(
            args.ip, vcenter_hostname, vcenter_uuid, 'active', 
            f"Connected. {content.about.version}", content.about.version
        )
        master_data_list.append(record)
        
        # KEŞİF BAŞLAT (Sadece Host Yolu)
        discover_host_path_only(content.rootFolder, record['component_moid'], vcenter_uuid, master_data_list)

    except Exception as e:
        # Hata kaydı
        record = create_vcenter_record(args.ip, vcenter_hostname, None, 'passive', str(e))
        if master_data_list and master_data_list[0].get("data_type") == "vmware_inventory_vcenter":
             master_data_list[0] = record
        else:
             master_data_list.insert(0, record)
    finally:
        if si: Disconnect(si)
        print(json.dumps(master_data_list, indent=2))

if __name__ == "__main__":
    main()
