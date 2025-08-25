import json
from datetime import datetime, timedelta, timezone

# JSON verisini yükle
INPUT_JSON_FILE = "energy_stats.json"
OUTPUT_SQL_FILE = "insert_server_power.txt"

def generate_filtered_insert_commands(json_file, output_file):
    """
    JSON dosyasındaki verileri SQL INSERT komutlarına dönüştürür, yalnızca belirli bir zaman aralığını seçer
    ve bir SQL dosyasına kaydeder.
    :param json_file: Giriş JSON dosyasının yolu
    :param output_file: Çıkış SQL dosyasının adı
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        # Şu anki zamanı UTC+3 olarak al ve 15 dakika öncesine git
        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)
        time_window_start = current_time - timedelta(minutes=15)

        print(f"Current Time (UTC+3): {current_time.isoformat()}")
        print(f"Time Window Start (UTC+3): {time_window_start.isoformat()}")

        with open(output_file, "w") as sql_file:
            processed_records = 0  # Yazılan kayıtları saymak için
            for record in data:
                try:
                    # JSON timestamp'i geçici olarak UTC+3 timezone ile offset-aware yap
                    record_timestamp = datetime.fromisoformat(record["timestamp"]).replace(tzinfo=utc_plus_3)

                    # Debugging: Hangi kayıt işleniyor?
                    print(f"Processing Record Timestamp: {record_timestamp.isoformat()}")

                    # Zaman filtresi: 15 dakikalık aralıkta değilse atla
                    if not (time_window_start <= record_timestamp <= current_time):
                        print(f"Record {record['timestamp']} is outside the time window.")
                        continue

                    # SQL INSERT komutunu oluştur
                    sql_command = f"""
                    INSERT INTO ibm_server_power (server_name, atom_id, timestamp, power_watts, mb0, mb1, mb2, mb3, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7, inlet_temp) VALUES ('{record['server_name']}', '{record['atom_id']}', '{record['timestamp']}',{record['power_watts']}, {record['temperature_mb']['mb0']}, {record['temperature_mb']['mb1']},{record['temperature_mb']['mb2']},{record['temperature_mb']['mb3']}, {record['temperature_cpu']['cpu0']}, {record['temperature_cpu']['cpu1']}, {record['temperature_cpu']['cpu2']}, {record['temperature_cpu']['cpu3']}, {record['temperature_cpu']['cpu4']}, {record['temperature_cpu']['cpu5']}, {record['temperature_cpu']['cpu6']}, {record['temperature_cpu']['cpu7']}, {record['temperature_inlet']});
                    """
                    sql_file.write(sql_command.strip() + "\n")
                    processed_records += 1
                except Exception as e:
                    print(f"Error processing record {record}: {e}")

            print(f"Processed {processed_records} records. SQL commands saved to {output_file}.")

    except Exception as e:
        print(f"An error occurred: {e}")

# Fonksiyonu çalıştır
generate_filtered_insert_commands(INPUT_JSON_FILE, OUTPUT_SQL_FILE)
