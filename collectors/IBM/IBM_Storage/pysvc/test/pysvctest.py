import json
import os
import re
from pysvc2 import Client
import paramiko


def load_config(file_path="/Datalake_Project/configuration_file.json"):
    """IBM Virtualize yapılandırmasını yükler."""
    with open(file_path, "r") as f:
        config_data = json.load(f)
        return config_data["IBM-Virtualize"]


def extract_timestamp(file_list):
    """Filenames içinden son iki zaman damgasını ayıklar (hhmmss formatında)."""
    timestamp_pattern = re.compile(r'_(\d{6})$')
    timestamps = set()

    for filename in file_list:
        match = timestamp_pattern.search(filename)
        if match:
            timestamps.add(match.group(1))

    return sorted(timestamps, reverse=True)[:2]


def get_latest_dumps(client, remote_path):
    """IBM Virtualize sisteminden dump dosya adlarını alır."""
    dumps = client.lsdumps(prefix=remote_path)
    filenames = [d['file_name'] for d in dumps]
    top_timestamps = extract_timestamp(filenames)
    selected_files = [
        f for f in filenames if any(f.endswith(f"_{ts}") for ts in top_timestamps)
    ]
    return selected_files


def download_files_sftp(host, username, password, remote_dir, local_dir, file_list):
    """Paramiko kullanarak dosyaları indirir."""
    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    os.makedirs(local_dir, exist_ok=True)

    for filename in file_list:
        remote_file = os.path.join(remote_dir, filename)
        local_file = os.path.join(local_dir, filename)
        print(f"İndiriliyor: {filename}")
        sftp.get(remote_file, local_file)

    sftp.close()
    transport.close()
    print(f"{len(file_list)} dosya indirildi → {local_dir}")


def main():
    config = load_config()
    remote_path = config.get("remote_path", "/dumps/iostats")
    local_path = config.get("local_path", ".")

    client = Client(
        host=config["host"],
        username=config["username"],
        password=config["password"]
    )

    print("IBM Virtualize bağlantısı kuruldu. Dump dosyaları aranıyor...")
    selected_files = get_latest_dumps(client, remote_path)

    if not selected_files:
        print("Uygun dosya bulunamadı.")
        return

    print(f"{len(selected_files)} dosya seçildi: {selected_files}")
    print("İndirme işlemi başlatılıyor...")

    download_files_sftp(
        config["host"],
        config["username"],
        config["password"],
        remote_path,
        local_path,
        selected_files
    )


if __name__ == "__main__":
    main()
