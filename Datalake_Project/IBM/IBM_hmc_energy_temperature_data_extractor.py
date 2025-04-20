from IBM_hmc_Stats_Processor import HMC
import json
import os # Import os module to handle file paths

# Define the path to the configuration file
CONFIG_FILE_PATH = "/Datalake_Project/configuration_file.json"

OUTPUT_JSON_FILE = "energy_stats.json"  # JSON dosya adı

def load_configuration(config_file_path):
    """
    Loads configuration data from a JSON file.
    :param config_file_path: Path to the configuration JSON file.
    :return: Dictionary containing the configuration data.
    """
    if not os.path.exists(config_file_path):
        print(f"Error: Configuration file not found at {config_file_path}")
        return None
    try:
        with open(config_file_path, "r") as f:
            config_data = json.load(f)
        return config_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from configuration file: {e}")
        return None
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        return None


def save_all_to_json(data, output_file):
    """
    Tüm verileri bir JSON dosyasına kaydeder.
    :param data: JSON'a yazılacak veriler (liste formatında)
    :param output_file: Çıkış dosyasının ismi
    """
    try:
        # Ensure the directory for the output file exists if needed
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_file, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved to {output_file}")
    except Exception as e:
        print(f"Error writing to JSON file: {e}")


def get_server_power_and_temperature(hmc_hostname, username, password, output_file):
    """
    Sunuculardan enerji (power) ve sıcaklık (temperature) verilerini al ve JSON dosyasına kaydet.
    :param hmc_hostname: HMC host adı veya IP adresi
    :param username: HMC kullanıcı adı
    :param password: HMC şifresi
    :param output_file: Çıkış dosyasının ismi
    """
    print(f"Attempting to connect to HMC: {hmc_hostname}")
    hmc_connection = HMC(hmc_hostname, username, password)
    hmc_connection.set_debug(False) # Consider making debug level configurable

    all_data = []  # Tüm verileri saklamak için liste

    try:
        # Tüm sunucuları listele ve Atom ID'leri al
        serverlist = hmc_connection.get_server_details_pcm()
        if not serverlist:
            print(f"No servers found on HMC: {hmc_hostname}")
            return # Exit function if no servers are found

        for server in serverlist:
            print(f"-> Processing server: {server.get('name', 'N/A')} (Atom ID: {server.get('atomid', 'N/A')}) on HMC {hmc_hostname}")

            # Energy metriklerine ait dosyaları al
            # Added checks for 'atomid' and 'name' keys
            server_atomid = server.get('atomid')
            server_name = server.get('name')

            if not server_atomid or not server_name:
                print(f"Skipping server due to missing atomid or name: {server}")
                continue

            filelist = hmc_connection.get_filenames_energy(server_atomid, server_name)

            if not filelist:
                 print(f"No energy files found for server: {server_name} on HMC {hmc_hostname}")
                 continue

            for file in filelist:
                print(f"-> Processing file: {file.get('filename', 'N/A')}")

                # Dosyadan enerji verilerini çek
                try:
                    # Added checks for 'url' and 'filename' keys
                    file_url = file.get('url')
                    file_filename = file.get('filename')

                    if not file_url or not file_filename:
                        print(f"Skipping file due to missing url or filename: {file}")
                        continue

                    stats = hmc_connection.get_stats(file_url, file_filename, "energy")
                    header, energy_stats = hmc_connection.extract_energy_stats(stats)

                    if not energy_stats:
                        print(f"No energy stats extracted for file {file_filename}")
                        continue

                    # JSON formatında kaydetmek için her kaydı hazırla
                    for stat in energy_stats:
                        # Using .get() with a default value to handle potentially missing keys in stat dictionary
                        record = {
                            "hmc_hostname": hmc_hostname, # Added HMC hostname to the record
                            "server_name": server_name,
                            "atom_id": server_atomid,
                            "timestamp": stat.get('time'),
                            "power_watts": stat.get('watts'),
                            "temperature_mb": {
                                "mb0": stat.get('mb0'),
                                "mb1": stat.get('mb1'),
                                "mb2": stat.get('mb2'),
                                "mb3": stat.get('mb3')
                            },
                            "temperature_cpu": {
                                "cpu0": stat.get('cpu0'),
                                "cpu1": stat.get('cpu1'),
                                "cpu2": stat.get('cpu2'),
                                "cpu3": stat.get('cpu3'),
                                "cpu4": stat.get('cpu4'),
                                "cpu5": stat.get('cpu5'),
                                "cpu6": stat.get('cpu6'),
                                "cpu7": stat.get('cpu7')
                            },
                            "temperature_inlet": stat.get('inlet')
                        }
                        all_data.append(record)

                except Exception as e:
                    print(f"Error extracting energy stats for file {file.get('filename', 'N/A')}: {e}")

        # Tüm verileri JSON dosyasına kaydet
        # save_all_to_json(all_data, output_file) # Moved saving to the main block to aggregate data from all HMCs

    except Exception as e:
        print(f"Error processing HMC {hmc_hostname}: {e}")
        # Optionally, you could log the error or handle it differently


if __name__ == "__main__":
    config = load_configuration(CONFIG_FILE_PATH)

    if config and "IBM-HMC" in config:
        hmc_config = config["IBM-HMC"]
        hmc_hostnames_str = hmc_config.get("hmc_hostname")
        hmc_user = hmc_config.get("hmc_user")
        hmc_password = hmc_config.get("hmc_password")

        if not hmc_hostnames_str or not hmc_user or not hmc_password:
            print("Error: Missing HMC configuration details (hostname, user, or password) in the config file.")
        else:
            # Split hostnames by comma and remove leading/trailing whitespace
            hmc_hostnames = [hostname.strip() for hostname in hmc_hostnames_str.split(',') if hostname.strip()]

            if not hmc_hostnames:
                 print("Error: No valid HMC hostnames found in the configuration.")
            else:
                all_aggregated_data = [] # List to hold data from all HMCs

                for hostname in hmc_hostnames:
                    # Call the function for each hostname. The function appends data to all_aggregated_data
                    # Modified get_server_power_and_temperature to return the data instead of saving directly
                    # Or modify it to accept the list to append to
                    # Let's modify get_server_power_and_temperature to return the data
                    hmc_data = get_server_power_and_temperature(hostname, hmc_user, hmc_password, OUTPUT_JSON_FILE)
                    if hmc_data:
                         all_aggregated_data.extend(hmc_data) # Extend the list with data from the current HMC

                # Save all aggregated data to the JSON file after processing all HMCs
                save_all_to_json(all_aggregated_data, OUTPUT_JSON_FILE)

    else:
        print("Error: 'IBM-HMC' section not found or configuration file could not be loaded.")

