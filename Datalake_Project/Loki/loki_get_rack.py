import requests
import json

json_file_path = "/Datalake_Project/configuration_file.json"
with open(json_file_path, "r") as file:
    config = json.load(file)

def fetch_all_racks(api_url, api_token):
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
    """Her türlü değeri güvenli bir şekilde string olarak dönüştür, None ise NULL."""
    if value is None:
        return "NULL"
    if not isinstance(value, str):
        value = str(value)
    escaped = value.replace("'", "''")
    return f"'{escaped}'"

def sql_null_or_value(value):
    """Sadece sayısal veya None değerler için kullan. None ise NULL, değilse direkt değer.
       Eğer sayısal değilse yine de hata verebilir. Bu durumda o alan için sql_str kullan."""
    if value is None:
        return "NULL"
    return str(value)

def bool_to_sql(value):
    return "TRUE" if value else "FALSE"

def generate_insert_queries(racks, table_name, batch_size=200):
    queries = []
    MAX_TAGS = 5

    for i in range(0, len(racks), batch_size):
        batch = racks[i:i+batch_size]
        values_list = []
        for rack in batch:
            # Numeric olduğunu bildiğimiz alanlar: id, u_height, starting_unit, weight, max_weight, device_count, powerfeed_count, vb.
            # Eğer emin değilseniz hepsini sql_str yapın.
            rack_id = sql_null_or_value(rack.get("id"))  
            rack_url = sql_str(rack.get("url"))
            rack_display = sql_str(rack.get("display"))
            rack_name = sql_str(rack.get("name"))
            facility_id = sql_null_or_value(rack.get("facility_id"))

            site = rack.get("site") or {}
            site_id = sql_null_or_value(site.get("id"))
            site_url = sql_str(site.get("url"))
            site_display = sql_str(site.get("display"))
            site_name = sql_str(site.get("name"))
            site_slug = sql_str(site.get("slug"))

            location = rack.get("location") or {}
            location_id = sql_null_or_value(location.get("id"))
            location_url = sql_str(location.get("url"))
            location_display = sql_str(location.get("display"))
            location_name = sql_str(location.get("name"))
            location_slug = sql_str(location.get("slug"))
            location_depth = sql_null_or_value(location.get("_depth"))

            tenant = sql_str(rack.get("tenant"))

            status = rack.get("status") or {}
            status_value = sql_str(status.get("value"))
            status_label = sql_str(status.get("label"))

            role = rack.get("role") or {}
            role_id = sql_null_or_value(role.get("id"))
            role_url = sql_str(role.get("url"))
            role_display = sql_str(role.get("display"))
            role_name = sql_str(role.get("name"))
            role_slug = sql_str(role.get("slug"))

            serial = sql_str(rack.get("serial"))
            asset_tag = sql_str(rack.get("asset_tag"))
            type_val = sql_str(rack.get("type"))

            width = rack.get("width") or {}
            width_value = sql_null_or_value(width.get("value"))
            width_label = sql_str(width.get("label"))

            u_height = sql_null_or_value(rack.get("u_height"))
            starting_unit = sql_null_or_value(rack.get("starting_unit"))
            weight = sql_null_or_value(rack.get("weight"))
            max_weight = sql_null_or_value(rack.get("max_weight"))
            weight_unit = sql_str(rack.get("weight_unit"))
            desc_units = bool_to_sql(rack.get("desc_units", False))

            outer_width = sql_null_or_value(rack.get("outer_width"))
            outer_depth = sql_null_or_value(rack.get("outer_depth"))

            outer_unit = rack.get("outer_unit") or {}
            outer_unit_value = sql_str(outer_unit.get("value"))
            outer_unit_label = sql_str(outer_unit.get("label"))

            mounting_depth = sql_null_or_value(rack.get("mounting_depth"))
            description = sql_str(rack.get("description"))
            comments = sql_str(rack.get("comments"))

            tags = rack.get("tags", [])
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

            custom_fields = rack.get("custom_fields", {})
            kabin_enerji = sql_str(custom_fields.get("Kabin_Enerji"))
            kabin_pdu_a_ip = sql_str(custom_fields.get("kabin_pdu_a_IP"))
            kabin_pdu_b_ip = sql_str(custom_fields.get("kabin_pdu_b_IP"))

            created = sql_str(rack.get("created"))
            last_updated = sql_str(rack.get("last_updated"))
            device_count = sql_null_or_value(rack.get("device_count"))
            powerfeed_count = sql_null_or_value(rack.get("powerfeed_count"))

            values = (
                f"({rack_id}, {rack_url}, {rack_display}, {rack_name}, {facility_id}, "
                f"{site_id}, {site_url}, {site_display}, {site_name}, {site_slug}, "
                f"{location_id}, {location_url}, {location_display}, {location_name}, {location_slug}, {location_depth}, "
                f"{tenant}, {status_value}, {status_label}, "
                f"{role_id}, {role_url}, {role_display}, {role_name}, {role_slug}, "
                f"{serial}, {asset_tag}, {type_val}, "
                f"{width_value}, {width_label}, {u_height}, {starting_unit}, {weight}, {max_weight}, {weight_unit}, {desc_units}, "
                f"{outer_width}, {outer_depth}, {outer_unit_value}, {outer_unit_label}, "
                f"{mounting_depth}, {description}, {comments}, "
                f"{tag_ids[0]}, {tag_urls[0]}, {tag_displays[0]}, {tag_names[0]}, {tag_slugs[0]}, {tag_colors[0]}, "
                f"{tag_ids[1]}, {tag_urls[1]}, {tag_displays[1]}, {tag_names[1]}, {tag_slugs[1]}, {tag_colors[1]}, "
                f"{tag_ids[2]}, {tag_urls[2]}, {tag_displays[2]}, {tag_names[2]}, {tag_slugs[2]}, {tag_colors[2]}, "
                f"{tag_ids[3]}, {tag_urls[3]}, {tag_displays[3]}, {tag_names[3]}, {tag_slugs[3]}, {tag_colors[3]}, "
                f"{tag_ids[4]}, {tag_urls[4]}, {tag_displays[4]}, {tag_names[4]}, {tag_slugs[4]}, {tag_colors[4]}, "
                f"{kabin_enerji}, {kabin_pdu_a_ip}, {kabin_pdu_b_ip}, "
                f"{created}, {last_updated}, {device_count}, {powerfeed_count})"
            )

            values_list.append(values)

        if values_list:
            query = (
                f"INSERT INTO {table_name} ("
                "id, url, display, name, facility_id, "
                "site_id, site_url, site_display, site_name, site_slug, "
                "location_id, location_url, location_display, location_name, location_slug, location_depth, "
                "tenant, status_value, status_label, "
                "role_id, role_url, role_display, role_name, role_slug, "
                "serial, asset_tag, type, "
                "width_value, width_label, u_height, starting_unit, weight, max_weight, weight_unit, desc_units, "
                "outer_width, outer_depth, outer_unit_value, outer_unit_label, "
                "mounting_depth, description, comments, "
                "tag1_id, tag1_url, tag1_display, tag1_name, tag1_slug, tag1_color, "
                "tag2_id, tag2_url, tag2_display, tag2_name, tag2_slug, tag2_color, "
                "tag3_id, tag3_url, tag3_display, tag3_name, tag3_slug, tag3_color, "
                "tag4_id, tag4_url, tag4_display, tag4_name, tag4_slug, tag4_color, "
                "tag5_id, tag5_url, tag5_display, tag5_name, tag5_slug, tag5_color, "
                "kabin_enerji, kabin_pdu_a_ip, kabin_pdu_b_ip, "
                "created, last_updated, device_count, powerfeed_count) VALUES "
                + ", ".join(values_list) + ";"
            )
            queries.append(query)

    return queries

if __name__ == "__main__":
# Extract values dynamically
    loki_config = config["Loki"]

    api_url = f"{loki_config['ip']}{loki_config['rack_endpoint']}"
    api_token = loki_config["api_token"]
    table_name = loki_config["rack_table_name"]


    all_racks = fetch_all_racks(api_url, api_token)
    queries = generate_insert_queries(all_racks, table_name, batch_size=200)

    for query in queries:
        print(query)