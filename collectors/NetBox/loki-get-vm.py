# -*- coding: utf-8 -*-
import requests
import json
import sys
from datetime import datetime, timezone

def load_config():
    with open("/Datalake_Project/configuration_file.json", "r") as file:
        config = json.load(file).get("Loki", {})
        required_keys = {'ip2', 'virtualization_endpoint', 'virtualization_table_name', 'api_token'}
        if missing := required_keys - config.keys():
            sys.exit(1)
        return config

def normalize_string(value):
    if value in (None, "", {}, []):
        return None
    return str(value)


def normalize_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def fetch_paginated_data(api_url, api_token):
    headers = {"Authorization": f"Token {api_token}"}
    results = []
    total_count = 0
    offset = 0
    limit = 1000
    
    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

    while True:
        try:
            url = f"{api_url}?limit={limit}&offset={offset}"
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not total_count:
                total_count = data.get('count', 0)
            
            current_results = data.get("results", [])
            if not current_results:
                break

            results.extend(current_results)
            offset += len(current_results)

            if len(current_results) < limit:
                break

        except requests.exceptions.HTTPError:
            sys.exit(1)
        except Exception:
            sys.exit(1)
    
    return results, total_count


def generate_vm_record(vm, total_count, collection_time):
    try:
        status = vm.get("status") or {}
        site = vm.get("site") or {}
        cluster = vm.get("cluster") or {}
        device = vm.get("device") or {}
        custom_fields = vm.get("custom_fields") or {}
        config_context = vm.get("config_context") or {}

        record = {
            "data_type": "netbox_inventory_vm",
            "count": normalize_int(total_count),
            "id": normalize_int(vm.get("id")),
            "url": normalize_string(vm.get("url")),
            "display_url": normalize_string(vm.get("display_url")),
            "display": normalize_string(vm.get("display")),
            "name": normalize_string(vm.get("name")),
            "status_value": normalize_string(status.get("value")),
            "status_label": normalize_string(status.get("label")),
            "site_id": normalize_int(site.get("id")),
            "site_url": normalize_string(site.get("url")),
            "site_display": normalize_string(site.get("display")),
            "site_name": normalize_string(site.get("name")),
            "site_slug": normalize_string(site.get("slug")),
            "site_description": normalize_string(site.get("description")),
            "cluster_id": normalize_int(cluster.get("id")),
            "cluster_url": normalize_string(cluster.get("url")),
            "cluster_display": normalize_string(cluster.get("display")),
            "cluster_name": normalize_string(cluster.get("name")),
            "cluster_description": normalize_string(cluster.get("description")),
            "device_id": normalize_int(device.get("id")),
            "device_url": normalize_string(device.get("url")),
            "device_display": normalize_string(device.get("display")),
            "device_name": normalize_string(device.get("name")),
            "device_description": normalize_string(device.get("description")),
            "serial": normalize_string(vm.get("serial")),
            "role": normalize_string(vm.get("role")),
            "tenant": normalize_string(vm.get("tenant")),
            "platform": normalize_string(vm.get("platform")),
            "primary_ip": normalize_string(vm.get("primary_ip")),
            "primary_ip4": normalize_string(vm.get("primary_ip4")),
            "primary_ip6": normalize_string(vm.get("primary_ip6")),
            "vcpus": normalize_int(vm.get("vcpus")),
            "memory": normalize_int(vm.get("memory")),
            "disk": normalize_int(vm.get("disk")),
            "description": normalize_string(vm.get("description")),
            "comments": normalize_string(vm.get("comments")),
            "config_template": normalize_string(vm.get("config_template")),
            "local_context_data": normalize_string(json.dumps(vm.get("local_context_data", None))),
            "config_context": normalize_string(json.dumps(config_context)),
        }

        tags = (vm.get("tags") or [])[:5]
        for index in range(5):
            tag = tags[index] if index < len(tags) else {}
            prefix = f"tags{index + 1}_"
            record[f"{prefix}id"] = normalize_int(tag.get("id"))
            record[f"{prefix}url"] = normalize_string(tag.get("url"))
            record[f"{prefix}display_url"] = normalize_string(tag.get("display_url"))
            record[f"{prefix}display"] = normalize_string(tag.get("display"))
            record[f"{prefix}name"] = normalize_string(tag.get("name"))
            record[f"{prefix}slug"] = normalize_string(tag.get("slug"))
            record[f"{prefix}color"] = normalize_string(tag.get("color"))

        record["custom_fields_config_instance_uuid"] = normalize_string(custom_fields.get("config_instance_uuid"))
        record["custom_fields_config_uuid"] = normalize_string(custom_fields.get("config_uuid"))
        record["custom_fields_datastore_name"] = normalize_string(custom_fields.get("datastore_name"))
        record["custom_fields_endpoint"] = normalize_string(custom_fields.get("endpoint"))
        record["custom_fields_guest_os"] = normalize_string(custom_fields.get("guest_os"))

        disks = (custom_fields.get("hard_disks_info") or [])[:5]
        for index in range(5):
            disk = disks[index] if index < len(disks) else {}
            prefix = f"custom_fields_hard_disk_info{index + 1}_"
            record[f"{prefix}label"] = normalize_string(disk.get("label"))
            record[f"{prefix}backing"] = normalize_string(disk.get("backing"))
            record[f"{prefix}capacity_kb"] = normalize_int(disk.get("capacity_kb"))

        record["custom_fields_ip_addresses"] = normalize_string(custom_fields.get("ip_addresses"))
        record["custom_fields_moid"] = normalize_string(custom_fields.get("moid"))
        record["custom_fields_musteri"] = normalize_string(custom_fields.get("musteri"))
        record["custom_fields_price_id"] = normalize_string(custom_fields.get("price_id"))
        record["custom_fields_uuid"] = normalize_string(custom_fields.get("uuid"))
        record["custom_fields_vm_name"] = normalize_string(custom_fields.get("vm_name"))
        record["custom_fields_vm_olusturulma_tarihi"] = normalize_string(custom_fields.get("vm_olusturulma_tarihi"))
        record["custom_fields_vmx_path"] = normalize_string(custom_fields.get("vmx_path"))
        record["created"] = normalize_string(vm.get("created"))
        record["last_updated"] = normalize_string(vm.get("last_updated"))
        record["interface_count"] = normalize_int(vm.get("interface_count"))
        record["virtual_disk_count"] = normalize_int(vm.get("virtual_disk_count"))
        record["collection_time"] = normalize_string(collection_time)

        return record

    except Exception:
        return None

def main():
    try:
        config = load_config()
        api_url = f"{config['ip2']}/{config['virtualization_endpoint']}"

        vms, total_count = fetch_paginated_data(api_url, config['api_token'])
        collection_time = datetime.now(timezone.utc).isoformat()

        records = []
        for vm in vms:
            record = generate_vm_record(vm, total_count, collection_time)
            if record:
                records.append(record)

        print(json.dumps(records))

    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
