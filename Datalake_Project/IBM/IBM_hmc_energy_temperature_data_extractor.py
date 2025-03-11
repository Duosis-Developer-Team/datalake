from IBM_hmc_Stats_Processor import HMC
import json

# Bağlantı bilgileri
CREDENTIALS = {
    "hmc_hostname": "10.34.2.110",
    "user": "zabbix",
    "passwd": "2u4Mzf7RJC",
}

OUTPUT_JSON_FILE = "energy_stats.json"  # JSON dosya adı

def save_all_to_json(data, output_file):
    """
    Tüm verileri bir JSON dosyasına kaydeder.
    :param data: JSON'a yazılacak veriler (liste formatında)
    :param output_file: Çıkış dosyasının ismi
    """
    try:
        with open(output_file, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved to {output_file}")
    except Exception as e:
        print(f"Error writing to JSON file: {e}")


def get_server_power_and_temperature(hmc_hostname, username, password):
    """
    Sunuculardan enerji (power) ve sıcaklık (temperature) verilerini al ve JSON dosyasına kaydet.
    :param hmc_hostname: HMC host adı veya IP adresi
    :param username: HMC kullanıcı adı
    :param password: HMC şifresi
    """
    hmc_connection = HMC(hmc_hostname, username, password)
    hmc_connection.set_debug(False)

    all_data = []  # Tüm verileri saklamak için liste

    try:
        # Tüm sunucuları listele ve Atom ID'leri al
        serverlist = hmc_connection.get_server_details_pcm()
        for server in serverlist:
            print(f"-> Processing server: {server['name']} (Atom ID: {server['atomid']})")

            # Energy metriklerine ait dosyaları al
            filelist = hmc_connection.get_filenames_energy(server['atomid'], server['name'])
            for file in filelist:
                print(f"-> Processing file: {file['filename']}")

                # Dosyadan enerji verilerini çek
                try:
                    stats = hmc_connection.get_stats(file['url'], file['filename'], "energy")
                    header, energy_stats = hmc_connection.extract_energy_stats(stats)

                    # JSON formatında kaydetmek için her kaydı hazırla
                    for stat in energy_stats:
                        record = {
                            "server_name": server['name'],
                            "atom_id": server['atomid'],
                            "timestamp": stat['time'],
                            "power_watts": stat['watts'],
                            "temperature_mb": {
                                "mb0": stat['mb0'],
                                "mb1": stat['mb1'],
                                "mb2": stat['mb2'],
                                "mb3": stat['mb3']
                            },
                            "temperature_cpu": {
                                "cpu0": stat['cpu0'],
                                "cpu1": stat['cpu1'],
                                "cpu2": stat['cpu2'],
                                "cpu3": stat['cpu3'],
                                "cpu4": stat['cpu4'],
                                "cpu5": stat['cpu5'],
                                "cpu6": stat['cpu6'],
                                "cpu7": stat['cpu7']
                            },
                            "temperature_inlet": stat['inlet']
                        }
                        all_data.append(record)

                except Exception as e:
                    print(f"Error extracting energy stats for file {file['filename']}: {e}")

        # Tüm verileri JSON dosyasına kaydet
        save_all_to_json(all_data, OUTPUT_JSON_FILE)

    except Exception as e:
        print(f"Error connecting to HMC: {e}")


if __name__ == "__main__":
    get_server_power_and_temperature(
        CREDENTIALS["hmc_hostname"], CREDENTIALS["user"], CREDENTIALS["passwd"]
    )
