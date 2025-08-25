# -*- coding: utf-8 -*-
import requests
import json

json_file_path = "/Datalake_Project/configuration_file.json"
with open(json_file_path, "r") as file:
    config = json.load(file)

def fetch_all_devices(api_url, api_token):
    headers = {
        "Authorization": f"Token {api_token}"
    }
    devices = []
    limit = 1000
    offset = 0

    while True:
        url = f"{api_url}?limit={limit}&offset={offset}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            break

        data = response.json()
        devices.extend(data.get("results", []))

        if data.get("next") is None:
            break

        offset += limit

    return devices

def sql_str(value):
    if value is None:
        return "NULL"
    if not isinstance(value, str):
        value = str(value)
    escaped = value.replace("'", "''")
    return f"'{escaped}'"

def sql_null_or_value(value):
    if value is None:
        return "NULL"
    return str(value)

def bool_to_sql(value):
    return "TRUE" if value else "FALSE"

def generate_insert_queries_for_devices(devices, table_name, batch_size=200):
    queries = []
    MAX_TAGS = 5

    for i in range(0, len(devices), batch_size):
        batch = devices[i:i+batch_size]
        values_list = []
        for dev in batch:
            dev_id = sql_null_or_value(dev.get("id"))
            dev_url = sql_str(dev.get("url"))
            dev_display = sql_str(dev.get("display"))
            dev_name = sql_str(dev.get("name"))

            device_type = dev.get("device_type") or {}
            device_type_id = sql_null_or_value(device_type.get("id"))
            device_type_url = sql_str(device_type.get("url"))
            device_type_display = sql_str(device_type.get("display"))
            device_type_name = sql_str(device_type.get("model"))
            device_type_slug = sql_str(device_type.get("slug"))

            manufacturer = device_type.get("manufacturer") or {}
            manufacturer_id = sql_null_or_value(manufacturer.get("id"))
            manufacturer_url = sql_str(manufacturer.get("url"))
            manufacturer_display = sql_str(manufacturer.get("display"))
            manufacturer_name = sql_str(manufacturer.get("name"))
            manufacturer_slug = sql_str(manufacturer.get("slug"))

            device_role = dev.get("device_role") or {}
            device_role_id = sql_null_or_value(device_role.get("id"))
            device_role_url = sql_str(device_role.get("url"))
            device_role_display = sql_str(device_role.get("display"))
            device_role_name = sql_str(device_role.get("name"))
            device_role_slug = sql_str(device_role.get("slug"))

            tenant = dev.get("tenant")
            if tenant and isinstance(tenant, dict):
                tenant_id = sql_null_or_value(tenant.get("id"))
            else:
                tenant_id = "NULL"

            platform = dev.get("platform")
            platform_id = "NULL"
            platform_name = "NULL"
            if platform and isinstance(platform, dict):
                platform_id = sql_null_or_value(platform.get("id"))
                platform_name = sql_str(platform.get("name"))

            serial = sql_str(dev.get("serial"))
            asset_tag = sql_str(dev.get("asset_tag"))

            site = dev.get("site") or {}
            site_id = sql_null_or_value(site.get("id"))
            site_url = sql_str(site.get("url"))
            site_display = sql_str(site.get("display"))
            site_name = sql_str(site.get("name"))
            site_slug = sql_str(site.get("slug"))

            location = dev.get("location") or {}
            location_id = sql_null_or_value(location.get("id"))
            location_url = sql_str(location.get("url"))
            location_display = sql_str(location.get("display"))
            location_name = sql_str(location.get("name"))
            location_slug = sql_str(location.get("slug"))
            location_depth = sql_null_or_value(location.get("_depth"))

            rack = dev.get("rack") or {}
            rack_id = sql_null_or_value(rack.get("id"))
            rack_url = sql_str(rack.get("url"))
            rack_display = sql_str(rack.get("display"))
            rack_name = sql_str(rack.get("name"))

            position = sql_null_or_value(dev.get("position"))

            face = dev.get("face") or {}
            face_value = sql_str(face.get("value"))
            face_label = sql_str(face.get("label"))

            latitude = sql_null_or_value(dev.get("latitude"))
            longitude = sql_null_or_value(dev.get("longitude"))

            parent_device = dev.get("parent_device")
            parent_device_id = "NULL"
            if parent_device and isinstance(parent_device, dict):
                parent_device_id = sql_null_or_value(parent_device.get("id"))

            status = dev.get("status") or {}
            status_value = sql_str(status.get("value"))
            status_label = sql_str(status.get("label"))

            airflow = dev.get("airflow") or {}
            airflow_value = sql_str(airflow.get("value"))
            airflow_label = sql_str(airflow.get("label"))

            primary_ip = dev.get("primary_ip") or {}
            primary_ip_id = sql_null_or_value(primary_ip.get("id"))
            primary_ip_address = "NULL"
            if primary_ip.get("address"):
                primary_ip_address = sql_str(primary_ip.get("address"))

            description = sql_str(dev.get("description"))
            comments = sql_str(dev.get("comments"))

            tags = dev.get("tags", [])
            tags = tags[:MAX_TAGS]
            tag_ids = []
            tag_urls = []
            tag_displays = []
            tag_names = []
            tag_slugs = []
            tag_colors = []
            for t in tags:
                tag_ids.append(sql_null_or_value(t.get("id")))
                tag_urls.append(sql_str(t.get("url")))
                tag_displays.append(sql_str(t.get("display")))
                tag_names.append(sql_str(t.get("name")))
                tag_slugs.append(sql_str(t.get("slug")))
                tag_colors.append(sql_str(t.get("color")))

            while len(tag_ids) < MAX_TAGS:
                tag_ids.append("NULL")
                tag_urls.append("NULL")
                tag_displays.append("NULL")
                tag_names.append("NULL")
                tag_slugs.append("NULL")
                tag_colors.append("NULL")

            custom_fields = dev.get("custom_fields", {})
            if custom_fields:
                cf_str = json.dumps(custom_fields).replace("'", "''")
                custom_fields_sql = f"'{cf_str}'"
            else:
                custom_fields_sql = "NULL"

            created = sql_str(dev.get("created"))
            last_updated = sql_str(dev.get("last_updated"))

            console_port_count = sql_null_or_value(dev.get("console_port_count"))
            console_server_port_count = sql_null_or_value(dev.get("console_server_port_count"))
            power_port_count = sql_null_or_value(dev.get("power_port_count"))
            power_outlet_count = sql_null_or_value(dev.get("power_outlet_count"))
            interface_count = sql_null_or_value(dev.get("interface_count"))
            front_port_count = sql_null_or_value(dev.get("front_port_count"))
            rear_port_count = sql_null_or_value(dev.get("rear_port_count"))
            device_bay_count = sql_null_or_value(dev.get("device_bay_count"))
            module_bay_count = sql_null_or_value(dev.get("module_bay_count"))
            inventory_item_count = sql_null_or_value(dev.get("inventory_item_count"))

            # collection_time kolonunu INSERT ifadesinde kullanmıyoruz, böylece DEFAULT NOW() devreye giriyor
            values = (
                f"({dev_id}, {dev_url}, {dev_display}, {dev_name}, "
                f"{device_type_id}, {device_type_url}, {device_type_display}, {device_type_name}, {device_type_slug}, "
                f"{manufacturer_id}, {manufacturer_url}, {manufacturer_display}, {manufacturer_name}, {manufacturer_slug}, "
                f"{device_role_id}, {device_role_url}, {device_role_display}, {device_role_name}, {device_role_slug}, "
                f"{tenant_id}, {platform_id}, {platform_name}, "
                f"{serial}, {asset_tag}, "
                f"{site_id}, {site_url}, {site_display}, {site_name}, {site_slug}, "
                f"{location_id}, {location_url}, {location_display}, {location_name}, {location_slug}, {location_depth}, "
                f"{rack_id}, {rack_url}, {rack_display}, {rack_name}, "
                f"{position}, {face_value}, {face_label}, "
                f"{latitude}, {longitude}, {parent_device_id}, "
                f"{status_value}, {status_label}, {airflow_value}, {airflow_label}, "
                f"{primary_ip_id}, {primary_ip_address}, "
                f"{description}, {comments}, "
                f"{tag_ids[0]}, {tag_urls[0]}, {tag_displays[0]}, {tag_names[0]}, {tag_slugs[0]}, {tag_colors[0]}, "
                f"{tag_ids[1]}, {tag_urls[1]}, {tag_displays[1]}, {tag_names[1]}, {tag_slugs[1]}, {tag_colors[1]}, "
                f"{tag_ids[2]}, {tag_urls[2]}, {tag_displays[2]}, {tag_names[2]}, {tag_slugs[2]}, {tag_colors[2]}, "
                f"{tag_ids[3]}, {tag_urls[3]}, {tag_displays[3]}, {tag_names[3]}, {tag_slugs[3]}, {tag_colors[3]}, "
                f"{tag_ids[4]}, {tag_urls[4]}, {tag_displays[4]}, {tag_names[4]}, {tag_slugs[4]}, {tag_colors[4]}, "
                f"{custom_fields_sql}, {created}, {last_updated}, "
                f"{console_port_count}, {console_server_port_count}, {power_port_count}, {power_outlet_count}, "
                f"{interface_count}, {front_port_count}, {rear_port_count}, {device_bay_count}, {module_bay_count}, {inventory_item_count})"
            )

            values_list.append(values)

        if values_list:
            query = (
                f"INSERT INTO {table_name} ("
                "id, url, display, name, "
                "device_type_id, device_type_url, device_type_display, device_type_name, device_type_slug, "
                "manufacturer_id, manufacturer_url, manufacturer_display, manufacturer_name, manufacturer_slug, "
                "device_role_id, device_role_url, device_role_display, device_role_name, device_role_slug, "
                "tenant_id, platform_id, platform_name, "
                "serial, asset_tag, "
                "site_id, site_url, site_display, site_name, site_slug, "
                "location_id, location_url, location_display, location_name, location_slug, location_depth, "
                "rack_id, rack_url, rack_display, rack_name, "
                "position, face_value, face_label, "
                "latitude, longitude, parent_device_id, "
                "status_value, status_label, airflow_value, airflow_label, "
                "primary_ip_id, primary_ip_address, "
                "description, comments, "
                "tag1_id, tag1_url, tag1_display, tag1_name, tag1_slug, tag1_color, "
                "tag2_id, tag2_url, tag2_display, tag2_name, tag2_slug, tag2_color, "
                "tag3_id, tag3_url, tag3_display, tag3_name, tag3_slug, tag3_color, "
                "tag4_id, tag4_url, tag4_display, tag4_name, tag4_slug, tag4_color, "
                "tag5_id, tag5_url, tag5_display, tag5_name, tag5_slug, tag5_color, "
                "custom_fields, created, last_updated, "
                "console_port_count, console_server_port_count, power_port_count, power_outlet_count, "
                "interface_count, front_port_count, rear_port_count, device_bay_count, module_bay_count, inventory_item_count"
                ") VALUES "
                + ", ".join(values_list) + ";"
            )
            queries.append(query)

    return queries

if __name__ == "__main__":
    loki_config = config["Loki"]

    api_url = f"{loki_config['ip']}{loki_config['device_endpoint']}"
    api_token = loki_config["api_token"]
    table_name = loki_config["device_table_name"]


    all_devices = fetch_all_devices(api_url, api_token)
    queries = generate_insert_queries_for_devices(all_devices, table_name, batch_size=200)

    for query in queries:
        print(query)
