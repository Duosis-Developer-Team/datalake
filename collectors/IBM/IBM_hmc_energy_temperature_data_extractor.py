from IBM_hmc_Stats_Processor import HMC
import json
import os
import sys


OUTPUT_JSON_FILE = "energy_stats.json"  # JSON dosya adı


def get_config_paths(config_path=None):
    """
    configuration_file.json icin kullanilacak yolu uretir.
    Termius ve sunucu kullaniminda ana beklenen konum /Datalake_Project/configuration_file.json.
    """
    if config_path:
        return [os.path.abspath(config_path)]

    return ["/Datalake_Project/configuration_file.json"]


def load_hmc_credentials(config_path=None):
    """
    IBM-HMC baglanti bilgilerini configuration_file.json dosyasindan okur.
    """
    errors = []

    for path in get_config_paths(config_path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                config_text = file.read()
        except FileNotFoundError:
            continue
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            continue

        try:
            hmc_config = extract_json_object_for_key(config_text, "IBM-HMC")
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
            continue

        credentials = {
            "hmc_hostname": hmc_config.get("hmc_hostname"),
            "user": hmc_config.get("hmc_user") or hmc_config.get("user"),
            "passwd": hmc_config.get("hmc_password") or hmc_config.get("passwd") or hmc_config.get("password"),
        }

        missing_fields = [
            field for field, value in credentials.items() if not value
        ]
        if missing_fields:
            errors.append(
                f"{path}: missing IBM-HMC values for {', '.join(missing_fields)}"
            )
            continue

        return credentials, path

    error_message = "Configuration file could not be loaded."
    if errors:
        error_message = f"{error_message} Checked paths: {'; '.join(errors)}"

    raise RuntimeError(error_message)


def extract_json_object_for_key(config_text, section_name):
    """
    Gecerli olmayan genel JSON icinden ilgili bolumu ayiklayip parse eder.
    Bu sayede configuration_file.json icinde alakasiz bir bolum bozuk olsa bile
    IBM-HMC ayarlari okunabilir.
    """
    section_marker = f'"{section_name}"'
    section_start = config_text.find(section_marker)
    if section_start == -1:
        raise ValueError(f"'{section_name}' section not found")

    object_start = config_text.find("{", section_start)
    if object_start == -1:
        raise ValueError(f"'{section_name}' section does not contain an object")

    brace_depth = 0
    in_string = False
    escape_next = False

    for index in range(object_start, len(config_text)):
        char = config_text[index]

        if escape_next:
            escape_next = False
            continue

        if char == "\\" and in_string:
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth == 0:
                try:
                    return json.loads(config_text[object_start:index + 1])
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"'{section_name}' section is not valid JSON ({exc})"
                    ) from exc

    raise ValueError(f"'{section_name}' section is not closed properly")


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
    try:
        config_file = sys.argv[1] if len(sys.argv) > 1 else None
        credentials, loaded_config_path = load_hmc_credentials(config_file)
        print(f"IBM-HMC configuration loaded from: {loaded_config_path}")
        get_server_power_and_temperature(
            credentials["hmc_hostname"],
            credentials["user"],
            credentials["passwd"],
        )
    except Exception as exc:
        print(f"Error loading IBM-HMC configuration: {exc}")
        sys.exit(1)
