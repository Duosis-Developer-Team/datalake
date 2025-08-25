# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime

# --- Yardımcı fonksiyonlar ---

def sql_str(val):
    if val is None:
        return "NULL"
    s = str(val).replace("'", "''")
    return f"'{s}'"

def sql_null(val):
    return "NULL" if val is None else str(val)

def bool_to_sql(val):
    if val is None:
        return "NULL"
    return "TRUE" if val else "FALSE"

def to_timestamptz(val):
    if not val:
        return "NULL"
    return f"{sql_str(val)}::timestamptz"

# --- Config yükleme ---
cfg_path = "/Datalake_Project/configuration_file.json"
with open(cfg_path, encoding="utf-8") as f:
    cfg = json.load(f)

loki = cfg.get("Loki", {})
api_ip     = loki.get("ip")
api_url    = api_ip + loki.get("device-type_endpoint")
api_token  = loki.get("api_token")
table_name = loki.get("device-type_table_name")

# --- Paginated fetch ---
def fetch_all_device_types(url, token):
    headers = {"Authorization": f"Token {token}"}
    items, limit, offset = [], 1000, 0
    while True:
        resp = requests.get(f"{url}?limit={limit}&offset={offset}", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("results", []))
        if not data.get("next"):
            break
        offset += limit
    return items

# --- Main: Create INSERT per record with all fields from response ---
if __name__ == "__main__":
    records = fetch_all_device_types(api_url, api_token)
    for rec in records:
        # Nested flatten
        m  = rec.get("manufacturer") or {}
        dp = rec.get("default_platform") or {}

        # Tags and custom_fields as JSON
        tags_json = sql_str(json.dumps(rec.get("tags", []), ensure_ascii=False))
        cf_json   = sql_str(json.dumps(rec.get("custom_fields", {}), ensure_ascii=False))

        cols = [
            "id","url","display_url","display",
            # manufacturer
            "manufacturer_id","manufacturer_url","manufacturer_display","manufacturer_name","manufacturer_slug",
            # default_platform
            "default_platform_id","default_platform_url","default_platform_display","default_platform_name",
            # model & identifiers
            "model","slug","part_number","u_height",
            # flags & attributes
            "exclude_from_utilization","is_full_depth","subdevice_role","airflow",
            "weight","weight_unit","front_image","rear_image",
            # text fields
            "description","comments",
            # arrays and JSON
            "tags","custom_fields",
            # timestamps
            "created","last_updated",
            # counts
            "device_count","console_port_template_count","console_server_port_template_count",
            "power_port_template_count","power_outlet_template_count","interface_template_count",
            "front_port_template_count","rear_port_template_count","device_bay_template_count",
            "module_bay_template_count","inventory_item_template_count"
        ]

        vals = [
            sql_null(rec.get("id")), sql_str(rec.get("url")), sql_str(rec.get("display_url")), sql_str(rec.get("display")),
            sql_null(m.get("id")), sql_str(m.get("url")), sql_str(m.get("display")), sql_str(m.get("name")), sql_str(m.get("slug")),
            sql_null(dp.get("id")), sql_str(dp.get("url")), sql_str(dp.get("display")) if dp.get("display") else sql_str(dp.get("name")), sql_str(dp.get("name")),
            sql_str(rec.get("model")), sql_str(rec.get("slug")), sql_str(rec.get("part_number")), sql_null(rec.get("u_height")),
            bool_to_sql(rec.get("exclude_from_utilization")), bool_to_sql(rec.get("is_full_depth")),
            sql_str(rec.get("subdevice_role")) if rec.get("subdevice_role") else "NULL",
            sql_str(rec.get("airflow")) if rec.get("airflow") else "NULL",
            sql_null(rec.get("weight")), sql_str(rec.get("weight_unit")) if rec.get("weight_unit") else "NULL",
            sql_str(rec.get("front_image")) if rec.get("front_image") else "NULL",
            sql_str(rec.get("rear_image")) if rec.get("rear_image") else "NULL",
            sql_str(rec.get("description")), sql_str(rec.get("comments")),
            tags_json, cf_json,
            to_timestamptz(rec.get("created")), to_timestamptz(rec.get("last_updated")),
            sql_null(rec.get("device_count")), sql_null(rec.get("console_port_template_count")),
            sql_null(rec.get("console_server_port_template_count")), sql_null(rec.get("power_port_template_count")),
            sql_null(rec.get("power_outlet_template_count")), sql_null(rec.get("interface_template_count")),
            sql_null(rec.get("front_port_template_count")), sql_null(rec.get("rear_port_template_count")),
            sql_null(rec.get("device_bay_template_count")), sql_null(rec.get("module_bay_template_count")),
            sql_null(rec.get("inventory_item_template_count"))
        ]

        insert_sql = (
            f"INSERT INTO {table_name} (" + ", ".join(cols) + ") VALUES (" + ", ".join(vals) + ");"
        )
        print(insert_sql)
