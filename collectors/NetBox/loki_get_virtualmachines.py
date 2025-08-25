# -*- coding: utf-8 -*-
import requests
import json
import sys
from datetime import datetime

def load_config():
    with open("/Datalake_Project/configuration_file.json", "r") as file:
        config = json.load(file).get("Loki", {})
        required_keys = {'ip2', 'virtualization_endpoint', 'virtualization_table_name', 'api_token'}
        if missing := required_keys - config.keys():
            sys.exit(1)
        return config

def sql_str(value):
    if value in (None, "", {}, []):
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return f"'{str(value).replace(chr(39), chr(39)*2)}'"

def sql_null_or_value(value):
    return "NULL" if value in (None, "") else str(value)

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

def generate_sql_values(vm, total_count):
    try:
        status = vm.get("status") or {}
        site = vm.get("site") or {}
        cluster = vm.get("cluster") or {}
        device = vm.get("device") or {}
        custom_fields = vm.get("custom_fields") or {}
        config_context = vm.get("config_context") or {}

        values = [
            sql_null_or_value(total_count),
            sql_null_or_value(vm.get("id")),
            sql_str(vm.get("url")),
            sql_str(vm.get("display_url")),
            sql_str(vm.get("display")),
            sql_str(vm.get("name")),
            sql_str(status.get("value")),
            sql_str(status.get("label")),
            sql_null_or_value(site.get("id")),
            sql_str(site.get("url")),
            sql_str(site.get("display")),
            sql_str(site.get("name")),
            sql_str(site.get("slug")),
            sql_str(site.get("description")),
            sql_null_or_value(cluster.get("id")),
            sql_str(cluster.get("url")),
            sql_str(cluster.get("display")),
            sql_str(cluster.get("name")),
            sql_str(cluster.get("description")),
            sql_null_or_value(device.get("id")),
            sql_str(device.get("url")),
            sql_str(device.get("display")),
            sql_str(device.get("name")),
            sql_str(device.get("description")),
            sql_str(vm.get("serial")),
            sql_str(vm.get("role")),
            sql_str(vm.get("tenant")),
            sql_str(vm.get("platform")),
            sql_str(vm.get("primary_ip")),
            sql_str(vm.get("primary_ip4")),
            sql_str(vm.get("primary_ip6")),
            sql_null_or_value(vm.get("vcpus")),
            sql_null_or_value(vm.get("memory")),
            sql_null_or_value(vm.get("disk")),
            sql_str(vm.get("description")),
            sql_str(vm.get("comments")),
            sql_str(vm.get("config_template")),
            sql_str(json.dumps(vm.get("local_context_data", None))),
            sql_str(json.dumps(config_context)),
        ]

        tags = (vm.get("tags") or [])[:5]
        for tag in tags:
            values.extend([
                sql_null_or_value(tag.get("id")),
                sql_str(tag.get("url")),
                sql_str(tag.get("display_url")),
                sql_str(tag.get("display")),
                sql_str(tag.get("name")),
                sql_str(tag.get("slug")),
                sql_str(tag.get("color"))
            ])
        for _ in range(5 - len(tags)):
            values.extend(["NULL"] * 7)

        values.extend([
            sql_str(custom_fields.get("config_instance_uuid")),
            sql_str(custom_fields.get("config_uuid")),
            sql_str(custom_fields.get("datastore_name")),
            sql_str(custom_fields.get("endpoint")),
            sql_str(custom_fields.get("guest_os")),
        ])

        disks = (custom_fields.get("hard_disks_info") or [])[:5]
        for disk in disks:
            values.extend([
                sql_str(disk.get("label")),
                sql_str(disk.get("backing")),
                sql_null_or_value(disk.get("capacity_kb"))
            ])
        for _ in range(5 - len(disks)):
            values.extend(["NULL"] * 3)

        values.extend([
            sql_str(custom_fields.get("ip_addresses")),
            sql_str(custom_fields.get("moid")),
            sql_str(custom_fields.get("musteri")),
            sql_str(custom_fields.get("price_id")),
            sql_str(custom_fields.get("uuid")),
            sql_str(custom_fields.get("vm_name")),
            sql_str(custom_fields.get("vm_olusturulma_tarihi")),
            sql_str(custom_fields.get("vmx_path")),
            sql_str(vm.get("created")),
            sql_str(vm.get("last_updated")),
            sql_null_or_value(vm.get("interface_count")),
            sql_null_or_value(vm.get("virtual_disk_count")),
            "NOW()"
        ])

        return values
        
    except Exception:
        return None

def main():
    try:
        config = load_config()
        api_url = f"{config['ip2']}/{config['virtualization_endpoint']}"
        
        vms, total_count = fetch_paginated_data(api_url, config['api_token'])
        
        columns = [
            'count', 'id', 'url', 'display_url', 'display', 'name',
            'status_value', 'status_label', 'site_id', 'site_url',
            'site_display', 'site_name', 'site_slug', 'site_description',
            'cluster_id', 'cluster_url', 'cluster_display', 'cluster_name',
            'cluster_description', 'device_id', 'device_url', 'device_display',
            'device_name', 'device_description', 'serial', 'role', 'tenant',
            'platform', 'primary_ip', 'primary_ip4', 'primary_ip6', 'vcpus',
            'memory', 'disk', 'description', 'comments', 'config_template',
            'local_context_data', 'config_context',
            'tags1_id', 'tags1_url', 'tags1_display_url', 'tags1_display', 'tags1_name', 'tags1_slug', 'tags1_color',
            'tags2_id', 'tags2_url', 'tags2_display_url', 'tags2_display', 'tags2_name', 'tags2_slug', 'tags2_color',
            'tags3_id', 'tags3_url', 'tags3_display_url', 'tags3_display', 'tags3_name', 'tags3_slug', 'tags3_color',
            'tags4_id', 'tags4_url', 'tags4_display_url', 'tags4_display', 'tags4_name', 'tags4_slug', 'tags4_color',
            'tags5_id', 'tags5_url', 'tags5_display_url', 'tags5_display', 'tags5_name', 'tags5_slug', 'tags5_color',
            'custom_fields_config_instance_uuid', 'custom_fields_config_uuid',
            'custom_fields_datastore_name', 'custom_fields_endpoint',
            'custom_fields_guest_os',
            'custom_fields_hard_disk_info1_label', 'custom_fields_hard_disk_info1_backing', 'custom_fields_hard_disk_info1_capacity_kb',
            'custom_fields_hard_disk_info2_label', 'custom_fields_hard_disk_info2_backing', 'custom_fields_hard_disk_info2_capacity_kb',
            'custom_fields_hard_disk_info3_label', 'custom_fields_hard_disk_info3_backing', 'custom_fields_hard_disk_info3_capacity_kb',
            'custom_fields_hard_disk_info4_label', 'custom_fields_hard_disk_info4_backing', 'custom_fields_hard_disk_info4_capacity_kb',
            'custom_fields_hard_disk_info5_label', 'custom_fields_hard_disk_info5_backing', 'custom_fields_hard_disk_info5_capacity_kb',
            'custom_fields_ip_addresses', 'custom_fields_moid', 
            'custom_fields_musteri', 'custom_fields_price_id', 'custom_fields_uuid',
            'custom_fields_vm_name', 'custom_fields_vm_olusturulma_tarihi',
            'custom_fields_vmx_path', 'created', 'last_updated',
            'interface_count', 'virtual_disk_count',
            'collection_time'
        ]
        
        batch_size = 1000
        
        for i in range(0, len(vms), batch_size):
            batch_values = []
            for vm in vms[i:i+batch_size]:
                if values := generate_sql_values(vm, total_count):
                    batch_values.append(f"({', '.join(values)})")
            
            if batch_values:
                query = (
                    f"INSERT INTO public.{config['virtualization_table_name']} "
                    f"({', '.join(columns)})\n"
                    f"VALUES {', '.join(batch_values)};"
                )
                print(query)
                
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
