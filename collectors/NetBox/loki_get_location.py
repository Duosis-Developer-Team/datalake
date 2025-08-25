# -*- coding: utf-8 -*-
import requests
import json

json_file_path = "/Datalake_Project/configuration_file.json"
with open(json_file_path, "r") as file:
    config = json.load(file)

def fetch_all_locations(api_url, api_token):
    headers = {
        "Authorization": f"Token {api_token}"
    }

    racks = []
    offset = 0
    limit = 1000

    while True:
        url = f"{api_url}?limit={limit}&offset={offset}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            break

        data = response.json()
        racks.extend(data.get("results", []))

        if data.get("next") is None:
            break
        offset += limit

    return racks

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

def generate_insert_queries_for_locations(locations, table_name, batch_size=200):
    queries = []
    MAX_TAGS = 5
    for i in range(0, len(locations), batch_size):
        batch = locations[i:i+batch_size]
        values_list = []
        for loc in batch:
            loc_id = sql_null_or_value(loc.get("id"))
            loc_url = sql_str(loc.get("url"))
            loc_display = sql_str(loc.get("display"))
            loc_name = sql_str(loc.get("name"))
            loc_slug = sql_str(loc.get("slug"))

            site = loc.get("site") or {}
            site_id = sql_null_or_value(site.get("id"))
            site_url = sql_str(site.get("url"))
            site_display = sql_str(site.get("display"))
            site_name = sql_str(site.get("name"))
            site_slug_ = sql_str(site.get("slug"))

            parent = loc.get("parent")
            if parent:
                # parent da site gibi bir yapıda geldiğini varsayıyoruz
                parent_id = sql_null_or_value(parent.get("id"))
                parent_url = sql_str(parent.get("url"))
                parent_display = sql_str(parent.get("display"))
                parent_name = sql_str(parent.get("name"))
                parent_slug = sql_str(parent.get("slug"))
            else:
                # parent yoksa NULL
                parent_id = "NULL"
                parent_url = "NULL"
                parent_display = "NULL"
                parent_name = "NULL"
                parent_slug = "NULL"

            status = loc.get("status") or {}
            status_value = sql_str(status.get("value"))
            status_label = sql_str(status.get("label"))

            tenant = loc.get("tenant")
            # tenant bir dict olabilir, biz sadece tenant_id saklarız
            if tenant and isinstance(tenant, dict):
                tenant_id = sql_null_or_value(tenant.get("id"))
            else:
                tenant_id = "NULL"

            description = sql_str(loc.get("description"))

            # Tags
            tags = loc.get("tags", [])
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

            custom_fields = loc.get("custom_fields", {})
            if custom_fields:
                cf_str = json.dumps(custom_fields).replace("'", "''")
                custom_fields_sql = f"'{cf_str}'"
            else:
                custom_fields_sql = "NULL"

            created = sql_str(loc.get("created"))
            last_updated = sql_str(loc.get("last_updated"))
            rack_count = sql_null_or_value(loc.get("rack_count"))
            device_count = sql_null_or_value(loc.get("device_count"))
            _depth = sql_null_or_value(loc.get("_depth"))

            values = (
                f"({loc_id}, {loc_url}, {loc_display}, {loc_name}, {loc_slug}, "
                f"{site_id}, {site_url}, {site_display}, {site_name}, {site_slug_}, "
                f"{parent_id}, {parent_url}, {parent_display}, {parent_name}, {parent_slug}, "
                f"{status_value}, {status_label}, "
                f"{tenant_id}, {description}, "
                f"{tag_ids[0]}, {tag_urls[0]}, {tag_displays[0]}, {tag_names[0]}, {tag_slugs[0]}, {tag_colors[0]}, "
                f"{tag_ids[1]}, {tag_urls[1]}, {tag_displays[1]}, {tag_names[1]}, {tag_slugs[1]}, {tag_colors[1]}, "
                f"{tag_ids[2]}, {tag_urls[2]}, {tag_displays[2]}, {tag_names[2]}, {tag_slugs[2]}, {tag_colors[2]}, "
                f"{tag_ids[3]}, {tag_urls[3]}, {tag_displays[3]}, {tag_names[3]}, {tag_slugs[3]}, {tag_colors[3]}, "
                f"{tag_ids[4]}, {tag_urls[4]}, {tag_displays[4]}, {tag_names[4]}, {tag_slugs[4]}, {tag_colors[4]}, "
                f"{custom_fields_sql}, {created}, {last_updated}, {rack_count}, {device_count}, {_depth})"
            )

            values_list.append(values)

        if values_list:
            query = (
                f"INSERT INTO {table_name} ("
                "id, url, display, name, slug, "
                "site_id, site_url, site_display, site_name, site_slug, "
                "parent_id, parent_url, parent_display, parent_name, parent_slug, "
                "status_value, status_label, "
                "tenant_id, description, "
                "tag1_id, tag1_url, tag1_display, tag1_name, tag1_slug, tag1_color, "
                "tag2_id, tag2_url, tag2_display, tag2_name, tag2_slug, tag2_color, "
                "tag3_id, tag3_url, tag3_display, tag3_name, tag3_slug, tag3_color, "
                "tag4_id, tag4_url, tag4_display, tag4_name, tag4_slug, tag4_color, "
                "tag5_id, tag5_url, tag5_display, tag5_name, tag5_slug, tag5_color, "
                "custom_fields, created, last_updated, rack_count, device_count, _depth) VALUES "
                + ", ".join(values_list) + ";"
            )
            queries.append(query)

    return queries

if __name__ == "__main__":
    loki_config = config["Loki"]

    api_url = f"{loki_config['ip']}{loki_config['location_endpoint']}"
    api_token = loki_config["api_token"]
    table_name = loki_config["location_table_name"]

    all_locations = fetch_all_locations(api_url, api_token)
    queries = generate_insert_queries_for_locations(all_locations, table_name, batch_size=200)

    for query in queries:
        print(query)
