import json
import ast
from datetime import datetime, timedelta

# Zaman filtreleme fonksiyonu
def is_within_time_range(timestamp, reference_time, time_difference_minutes):
    try:
        parsed_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
        time_limit = reference_time - timedelta(minutes=time_difference_minutes)
        return parsed_time >= time_limit and parsed_time <= reference_time and parsed_time.second == 0
    except ValueError:
        print(f"Geçersiz zaman formatı: {timestamp}")
        return False

# Tags ve fields birleşiminden tekrar eden anahtarları kaldıran fonksiyon
def merge_tags_and_fields(tags, fields):
    # Tüm anahtarları küçük harfe çevirerek birleştir
    merged_data = {k.lower(): v for k, v in {**tags, **fields}.items()}
    return merged_data

# JSON formatını düzeltme ve parse etme
def fix_and_parse_json(file_path):
    corrected_data = []
    with open(file_path, 'r') as f:
        for line in f:
            try:
                corrected_line = line.replace("'", '"')
                corrected_data.append(json.loads(corrected_line))
            except json.JSONDecodeError:
                try:
                    corrected_data.append(ast.literal_eval(line))
                except (SyntaxError, ValueError) as e:
                    print(f"Satır işlenemedi: {line.strip()} - Hata: {e}")
    return corrected_data

# SQL sorgularını oluşturma
def create_sql_queries_with_time_filter(file_path, time_difference_minutes=15):
    data = fix_and_parse_json(file_path)
    current_time = datetime.now().astimezone()

    insert_queries = []
    server_general_data = {}
    vios_general_data = {}
    lpar_general_data = {}

    repeat_measurements = [
        "vios_network_virtual", "vios_storage_physical", "vios_storage_FC",
        "vios_network_generic", "vios_storage_virtual", "lpar_storage_vFC", "lpar_net_virtual"
    ]

    for entry in data:
        measurement = entry.get("measurement", "")
        tags = entry.get("tags", {})
        fields = entry.get("fields", {})
        timestamp = entry.get("time", "")

        if not is_within_time_range(timestamp, current_time, time_difference_minutes):
            continue

        # Tekrarlayan anahtarları birleştirerek kaldır
        merged_data = merge_tags_and_fields(tags, fields)

        if measurement not in repeat_measurements:
            # Server General
            if "servername" in tags and "viosname" not in tags and "lparname" not in tags:
                key = (tags.get("servername", "").lower(), timestamp)
                if key not in server_general_data:
                    server_general_data[key] = {}
                server_general_data[key].update({f"{measurement}_{k}": v for k, v in merged_data.items()})

            # Vios General
            elif "servername" in tags and "viosname" in tags:
                key = (tags.get("servername", "").lower(), tags.get("viosname", "").lower(), timestamp)
                if key not in vios_general_data:
                    vios_general_data[key] = {}
                vios_general_data[key].update({f"{measurement}_{k}": v for k, v in merged_data.items()})

            # Lpar General
            elif "servername" in tags and "lparname" in tags:
                key = (tags.get("servername", "").lower(), tags.get("lparname", "").lower(), timestamp)
                if key not in lpar_general_data:
                    lpar_general_data[key] = {}
                lpar_general_data[key].update({f"{measurement}_{k}": v for k, v in merged_data.items()})
        else:
            table_name = f"ibm_{measurement}"
            columns = list(merged_data.keys()) + ["time"]
            values = list(merged_data.values()) + [timestamp]
            columns_str = ", ".join(columns)
            values_str = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"
            insert_queries.append(query)

    # Genel tablolar için sorguları oluştur
    for (servername, timestamp), fields in server_general_data.items():
        table_name = "ibm_server_general"
        fields.update({"servername": servername, "time": timestamp})
        columns = fields.keys()
        values = fields.values()
        columns_str = ", ".join(columns)
        values_str = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"
        insert_queries.append(query)

    for (servername, viosname, timestamp), fields in vios_general_data.items():
        table_name = "ibm_vios_general"
        fields.update({"servername": servername, "viosname": viosname, "time": timestamp})
        columns = fields.keys()
        values = fields.values()
        columns_str = ", ".join(columns)
        values_str = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"
        insert_queries.append(query)

    for (servername, lparname, timestamp), fields in lpar_general_data.items():
        table_name = "ibm_lpar_general"
        fields.update({"servername": servername, "lparname": lparname, "time": timestamp})
        columns = fields.keys()
        values = fields.values()
        columns_str = ", ".join(columns)
        values_str = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"
        insert_queries.append(query)

    return insert_queries

# Dosya yolu ve çalıştırma
file_path = "output.json"
queries = create_sql_queries_with_time_filter(file_path)

# SQL sorgularını dosyaya yaz
with open("insert_commands.txt", "w") as f:
    for query in queries:
        f.write(query + "\n")

print("SQL sorguları insert_commands.txt dosyasına yazıldı.")
